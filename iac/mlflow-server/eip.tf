resource "aws_eip" "mlflow_eip" {
  domain = "vpc"
}

resource "aws_eip_association" "mlflow_eip_assoc" {
  instance_id   = aws_instance.mlflow_server.id
  allocation_id = aws_eip.mlflow_eip.id
}