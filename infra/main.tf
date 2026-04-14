module "vpc" {
  source      = "./modules/vpc"
  environment = var.environment
  aws_region  = var.aws_region
}

module "s3" {
  source      = "./modules/s3"
  environment = var.environment
  aws_region  = var.aws_region
}

module "ecr" {
  source      = "./modules/ecr"
  environment = var.environment
}

# ECS security group defined here to break the ALB ↔ ECS cycle
resource "aws_security_group" "ecs" {
  name        = "medi-nudge-${var.environment}-ecs"
  description = "ECS tasks"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [module.alb.alb_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "medi-nudge-${var.environment}-ecs"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

module "alb" {
  source              = "./modules/alb"
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  public_subnet_ids   = module.vpc.public_subnet_ids
  acm_certificate_arn = var.acm_certificate_arn_apigw
}

module "rds" {
  source             = "./modules/rds"
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids
  ecs_sg_id          = aws_security_group.ecs.id
  db_instance_class  = var.db_instance_class
  db_multi_az        = var.db_multi_az
}

module "iam" {
  source              = "./modules/iam"
  environment         = var.environment
  aws_region          = var.aws_region
  aws_account_id      = data.aws_caller_identity.current.account_id
  media_bucket_arn    = module.s3.media_bucket_arn
  frontend_bucket_arn = module.s3.frontend_bucket_arn
  github_org          = var.github_org
  github_repo         = var.github_repo
  ecr_repo_arn        = module.ecr.repository_arn
  ecs_cluster_arn     = module.ecs.cluster_arn
}

module "ecs" {
  source                 = "./modules/ecs"
  environment            = var.environment
  aws_region             = var.aws_region
  aws_account_id         = data.aws_caller_identity.current.account_id
  vpc_id                 = module.vpc.vpc_id
  private_subnet_ids     = module.vpc.private_subnet_ids
  alb_target_group_arn   = module.alb.target_group_arn
  alb_sg_id              = module.alb.alb_sg_id
  ecs_sg_id              = aws_security_group.ecs.id
  ecr_repository_url     = module.ecr.repository_url
  media_bucket_name      = module.s3.media_bucket_name
  db_secret_arn          = module.rds.db_secret_arn
  task_role_arn          = module.iam.ecs_task_role_arn
  execution_role_arn     = module.iam.ecs_execution_role_arn
  api_desired_count      = var.ecs_api_desired_count
}

module "cloudfront" {
  source                          = "./modules/cloudfront"
  environment                     = var.environment
  frontend_bucket_regional_domain = module.s3.frontend_bucket_regional_domain
  alb_dns_name                    = module.alb.alb_dns_name
  acm_certificate_arn             = var.acm_certificate_arn_cloudfront
  frontend_domain                 = var.frontend_domain

  providers = {
    aws = aws.us_east_1
  }
}

data "aws_caller_identity" "current" {}

# S3 bucket policy for CloudFront OAC access — defined at root level so Terraform
# can establish an explicit dependency on both the S3 bucket and the CloudFront
# distribution, preventing the 307 TemporaryRedirect race condition on non-us-east-1 buckets.
data "aws_iam_policy_document" "frontend_bucket_policy" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions   = ["s3:GetObject"]
    resources = ["${module.s3.frontend_bucket_arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [module.cloudfront.cloudfront_distribution_arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  provider   = aws
  bucket     = module.s3.frontend_bucket_id
  policy     = data.aws_iam_policy_document.frontend_bucket_policy.json
  depends_on = [module.s3, module.cloudfront]
}
