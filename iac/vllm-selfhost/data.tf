# ---------------------------------------------------------------------------
# Encryption key shared by the data tier (S3 models, Aurora, Redis, secrets)
# ---------------------------------------------------------------------------
resource "aws_kms_key" "data" {
  description             = "${local.name} data encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_kms_alias" "data" {
  name          = "alias/${local.name}-data"
  target_key_id = aws_kms_key.data.key_id
}

# ---------------------------------------------------------------------------
# Model artifacts (S3). vLLM streams weights from here with the Run:ai model
# streamer, so every replica in every AZ reads the same artifact.
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "models" {
  bucket        = "${local.name}-models-${local.account_id}"
  force_destroy = !var.deletion_protection
}

resource "aws_s3_bucket_public_access_block" "models" {
  bucket                  = aws_s3_bucket.models.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    bucket_key_enabled = true

    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data.arn
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    id     = "expire-noncurrent"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 3
    }
  }

  depends_on = [aws_s3_bucket_versioning.models]
}

data "aws_iam_policy_document" "models_bucket" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.models.arn, "${aws_s3_bucket.models.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "models" {
  bucket = aws_s3_bucket.models.id
  policy = data.aws_iam_policy_document.models_bucket.json

  depends_on = [aws_s3_bucket_public_access_block.models]
}

# ---------------------------------------------------------------------------
# Container registry (mirror of the vLLM image; see scripts/mirror-image.sh)
# ---------------------------------------------------------------------------
resource "aws_ecr_repository" "vllm" {
  name                 = "${local.name}/vllm-openai"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = !var.deletion_protection

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.data.arn
  }
}

resource "aws_ecr_lifecycle_policy" "vllm" {
  repository = aws_ecr_repository.vllm.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the 20 most recent images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = { type = "expire" }
    }]
  })
}

# ---------------------------------------------------------------------------
# LiteLLM state: Aurora PostgreSQL Serverless v2 (keys, budgets, spend)
# ---------------------------------------------------------------------------
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "main" {
  name       = local.name
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "db" {
  name        = "${local.name}-aurora"
  description = "PostgreSQL from cluster nodes and pods"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
}

resource "aws_rds_cluster" "litellm" {
  cluster_identifier = "${local.name}-litellm"
  engine             = "aurora-postgresql"
  engine_mode        = "provisioned"
  engine_version     = var.aurora_engine_version
  database_name      = "litellm"
  master_username    = "litellm"
  master_password    = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  storage_encrypted = true
  kms_key_id        = aws_kms_key.data.arn

  backup_retention_period         = 7
  preferred_backup_window         = "18:00-19:00"
  copy_tags_to_snapshot           = true
  deletion_protection             = var.deletion_protection
  skip_final_snapshot             = !var.deletion_protection
  final_snapshot_identifier       = var.deletion_protection ? "${local.name}-litellm-final" : null
  apply_immediately               = !var.deletion_protection
  enabled_cloudwatch_logs_exports = ["postgresql"]

  serverlessv2_scaling_configuration {
    min_capacity = var.aurora_min_acu
    max_capacity = var.aurora_max_acu
  }
}

# One writer + one reader in different AZs for failover.
resource "aws_rds_cluster_instance" "litellm" {
  count = 2

  identifier           = "${local.name}-litellm-${count.index}"
  cluster_identifier   = aws_rds_cluster.litellm.id
  instance_class       = "db.serverless"
  engine               = aws_rds_cluster.litellm.engine
  engine_version       = aws_rds_cluster.litellm.engine_version
  db_subnet_group_name = aws_db_subnet_group.main.name
  availability_zone    = local.azs[count.index % length(local.azs)]
}

# ---------------------------------------------------------------------------
# Rate-limit counters: ElastiCache Redis (multi-AZ, TLS, auth token)
# ---------------------------------------------------------------------------
resource "random_password" "redis" {
  length  = 32
  special = false
}

resource "aws_elasticache_subnet_group" "main" {
  name       = local.name
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "redis" {
  name        = "${local.name}-redis"
  description = "Redis from cluster nodes and pods"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Redis from EKS nodes"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${local.name}-rl"
  description          = "LiteLLM rate limiting"

  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = var.redis_node_type
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled           = true

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  kms_key_id                 = aws_kms_key.data.arn
  transit_encryption_enabled = true
  auth_token                 = random_password.redis.result

  snapshot_retention_limit = 1
  apply_immediately        = !var.deletion_protection
}

# ---------------------------------------------------------------------------
# Gateway secrets (synced into the cluster by External Secrets Operator)
# ---------------------------------------------------------------------------
resource "random_password" "litellm_master_key" {
  length  = 48
  special = false
}

# Do not rotate: LiteLLM uses it to encrypt credentials stored in its database.
resource "random_password" "litellm_salt_key" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret" "gateway" {
  name                    = "${local.name}/gateway"
  description             = "LiteLLM gateway credentials"
  kms_key_id              = aws_kms_key.data.arn
  recovery_window_in_days = var.deletion_protection ? 30 : 0
}

resource "aws_secretsmanager_secret_version" "gateway" {
  secret_id = aws_secretsmanager_secret.gateway.id

  secret_string = jsonencode({
    LITELLM_MASTER_KEY = "sk-${random_password.litellm_master_key.result}"
    LITELLM_SALT_KEY   = "sk-${random_password.litellm_salt_key.result}"
    DATABASE_URL       = "postgresql://litellm:${random_password.db.result}@${aws_rds_cluster.litellm.endpoint}:5432/litellm"
    REDIS_URL          = "rediss://:${random_password.redis.result}@${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"
  })
}
