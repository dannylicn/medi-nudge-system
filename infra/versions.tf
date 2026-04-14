terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    # Configured per-environment via -backend-config flags or backend.hcl
    # Example:
    #   terraform init -backend-config="bucket=medi-nudge-tfstate-prod" \
    #                  -backend-config="key=prod/terraform.tfstate" \
    #                  -backend-config="region=ap-southeast-1" \
    #                  -backend-config="dynamodb_table=medi-nudge-tfstate-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "medi-nudge"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ACM certificate for CloudFront MUST be in us-east-1
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "medi-nudge"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
