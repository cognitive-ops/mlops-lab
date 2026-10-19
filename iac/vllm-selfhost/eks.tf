data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  common_tags = merge({
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "Terraform"
  }, var.tags)

  cluster_name = "${var.project_name}-${var.environment}"
  azs          = slice(data.aws_availability_zones.available.names, 0, var.az_count)
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.16"

  name = local.cluster_name
  cidr = var.vpc_cidr
  azs  = local.azs

  private_subnets = [for i in range(var.az_count) : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnets  = [for i in range(var.az_count) : cidrsubnet(var.vpc_cidr, 8, 200 + i)]

  enable_nat_gateway   = true
  single_nat_gateway   = var.single_nat_gateway
  enable_dns_hostnames = true

  # Subnet tags let Kubernetes place internet-facing / internal load balancers.
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.31"

  cluster_name    = local.cluster_name
  cluster_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access       = true
  cluster_endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs

  # Grants the identity that runs `terraform apply` cluster-admin.
  enable_cluster_creator_admin_permissions = true

  cluster_addons = {
    coredns    = {}
    kube-proxy = {}
    vpc-cni    = {}
    # Backs the PVC that caches model weights. Permissions come from the node
    # role (see iam_role_additional_policies below); use IRSA/Pod Identity in prod.
    aws-ebs-csi-driver = {}
  }

  eks_managed_node_groups = {
    # CPU pool for system pods (CoreDNS, EBS CSI controller, ...).
    system = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.system_node_instance_types
      min_size       = 1
      max_size       = 3
      desired_size   = var.system_node_count

      iam_role_additional_policies = {
        ebs_csi = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
      }
    }

    # GPU pool. The AL2023 NVIDIA AMI ships the driver and container runtime;
    # the device plugin DaemonSet (k8s/nvidia-device-plugin.yaml) exposes
    # nvidia.com/gpu to the scheduler.
    gpu = {
      ami_type       = "AL2023_x86_64_NVIDIA"
      instance_types = [var.gpu_instance_type]
      capacity_type  = var.gpu_use_spot ? "SPOT" : "ON_DEMAND"

      min_size     = var.gpu_node_min_count
      max_size     = var.gpu_node_max_count
      desired_size = var.gpu_node_desired_count

      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = var.gpu_disk_size_gb
            volume_type           = "gp3"
            encrypted             = true
            delete_on_termination = true
          }
        }
      }

      labels = {
        workload = "llm-inference"
      }

      # Keep non-GPU pods off expensive nodes.
      taints = {
        gpu = {
          key    = "sku"
          value  = "gpu"
          effect = "NO_SCHEDULE"
        }
      }
    }
  }
}
