provider "aws" {
  region = var.aws_region
  alias  = "acme-development"
  assume_role {
    role_arn = "arn:aws:iam::831704124374:role/OrganizationAccountAccessRole"
  }

}

provider "aws" {
  alias  = "acme_vpc"
  region = var.aws_region
  assume_role {
    role_arn = "arn:aws:iam::317555126509:role/TerraformDevelopment"
  }
}