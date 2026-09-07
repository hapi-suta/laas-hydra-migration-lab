terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.94"
    }
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.expected_account_id]
  default_tags {
    tags = { Project = var.name, Purpose = "hydra-customer-practice", ManagedBy = "terraform", Owner = var.owner_label, ReviewAfter = var.review_after }
  }
}
