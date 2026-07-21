resource "aws_instance" "mlflow_server" {
  ami                    = "ami-04b4f1a9cf54c11d0"
  instance_type          = var.instance_type
  subnet_id              = element(data.aws_subnets.default.ids, 0) #"subnet-0bd90a74c9b0a1d65"
  vpc_security_group_ids = [aws_security_group.mlflow_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.mlflow_profile.name

  root_block_device {
    volume_size = 32
    volume_type = "gp3"
  }
  user_data = <<-EOF
#!/bin/bash

set -e  # Exit script if any command fails

# Update system
sudo apt update -y
sudo apt install -y python3 python3-pip unzip curl certbot python3-certbot-nginx nginx python3-venv jq postgresql

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify AWS CLI installation
aws --version

# Create a virtual environment for MLflow
python3 -m venv /home/ubuntu/mlflow-env
source /home/ubuntu/mlflow-env/bin/activate
pip install --upgrade pip

# Install MLflow dependencies
pip install 'mlflow[auth]' boto3 psycopg2-binary

# Fetch the RDS password from Secrets Manager
RDS_PASSWORD=$(aws secretsmanager get-secret-value --secret-id mlflow-db-password --query SecretString --output text)

# Fetch MLflow auth credentials from Secrets Manager
MLFLOW_AUTH=$(aws secretsmanager get-secret-value --secret-id mlflow-auth-credentials --query SecretString --output text)
MLFLOW_ADMIN_USERNAME=$(echo $MLFLOW_AUTH | jq -r .username)
MLFLOW_ADMIN_PASSWORD=$(echo $MLFLOW_AUTH | jq -r .password)
MLFLOW_FLASK_SECRET=$(echo $MLFLOW_AUTH | jq -r .flask_secret_key)

# Set environment variables
echo "MLFLOW_DB_USER=${var.mlflow_db_user}" | sudo tee -a /etc/environment
echo "MLFLOW_DB_PASSWORD=$RDS_PASSWORD" | sudo tee -a /etc/environment
echo "MLFLOW_DB_HOST=${aws_db_instance.mlflow_db.address}" | sudo tee -a /etc/environment
echo "MLFLOW_S3_BUCKET=${var.mlflow_s3_bucket}" | sudo tee -a /etc/environment
echo "MLFLOW_AUTH_CONFIG_PATH=/home/ubuntu/mlflow-auth/basic_auth.ini" | sudo tee -a /etc/environment
echo "MLFLOW_ADMIN_USERNAME=$MLFLOW_ADMIN_USERNAME" | sudo tee -a /etc/environment
echo "MLFLOW_ADMIN_PASSWORD=$MLFLOW_ADMIN_PASSWORD" | sudo tee -a /etc/environment
echo "MLFLOW_FLASK_SERVER_SECRET_KEY=$MLFLOW_FLASK_SECRET" | sudo tee -a /etc/environment

# Load environment variables
source /etc/environment
export $(cat /etc/environment | xargs)

# Create MLflow auth configuration
mkdir -p /home/ubuntu/mlflow-auth
cat > /home/ubuntu/mlflow-auth/basic_auth.ini <<AUTHCONFIG
[mlflow]
default_permission = READ
database_uri = sqlite:////home/ubuntu/mlflow-auth/basic_auth.db
admin_username = $MLFLOW_ADMIN_USERNAME
admin_password = $MLFLOW_ADMIN_PASSWORD
authorization_function = mlflow.server.auth:authenticate_request_basic_auth
AUTHCONFIG

chown -R ubuntu:ubuntu /home/ubuntu/mlflow-auth
chmod 600 /home/ubuntu/mlflow-auth/basic_auth.ini

# Create MLflow systemd service
echo "Creating MLflow systemd service..."
sudo tee /etc/systemd/system/mlflow.service <<EOL
[Unit]
Description=MLflow Tracking Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="MLFLOW_DB_USER=$MLFLOW_DB_USER"
Environment="MLFLOW_DB_PASSWORD=$MLFLOW_DB_PASSWORD"
Environment="MLFLOW_DB_HOST=$MLFLOW_DB_HOST"
Environment="MLFLOW_S3_BUCKET=$MLFLOW_S3_BUCKET"
Environment="MLFLOW_AUTH_CONFIG_PATH=/home/ubuntu/mlflow-auth/basic_auth.ini"
Environment="MLFLOW_FLASK_SERVER_SECRET_KEY=$MLFLOW_FLASK_SERVER_SECRET_KEY"
ExecStart=/home/ubuntu/mlflow-env/bin/mlflow server \
    --backend-store-uri postgresql://$MLFLOW_DB_USER:$MLFLOW_DB_PASSWORD@$MLFLOW_DB_HOST/mlflowdb \
    --artifacts-destination s3://$MLFLOW_S3_BUCKET \
    --host 0.0.0.0 --port 5000 \
    --app-name basic-auth
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Start MLflow as a systemd service
sudo systemctl daemon-reload
sudo systemctl enable mlflow
sudo systemctl start mlflow

# Configure Nginx as a Reverse Proxy for MLflow
echo "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/mlflow <<EOL
server {
    listen 80;
    server_name mlflow.scopicdev.com;

    location / {
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

# Enable Nginx site and restart
sudo ln -s /etc/nginx/sites-available/mlflow /etc/nginx/sites-enabled/
sudo systemctl restart nginx

sleep 5

# Install SSL Certificate using Certbot
echo "Installing SSL certificate..."
sudo certbot --nginx -d mlflow.scopicdev.com --non-interactive --agree-tos --email femi.a@scopicsoftware.com

# Update Nginx main config for security
sudo sed -i 's/# server_tokens off;/server_tokens off;/' /etc/nginx/nginx.conf

sudo systemctl restart nginx
EOF

  key_name = "femi-scopic-development"

  depends_on = [aws_db_instance.mlflow_db]

  tags = {
    Name = "dev-use1-ec2-mlflow"
  }
}

resource "aws_security_group" "mlflow_sg" {
  name        = "mlflow-sg"
  description = "Security group for MLflow server"

  vpc_id = data.aws_vpc.default.id

  # Allow MLflow clients (adjust to your network)
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]

  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]

  }

  # Allow SSH for admin access (Optional - Restrict to your IP)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["85.107.72.119/32"] # Change this to your IP
  }

  # Allow all outgoing traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}