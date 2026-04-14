output "alb_dns_name" {
  description = "ALB DNS name — create a CNAME record for api_domain pointing here"
  value       = module.alb.alb_dns_name
}

output "cloudfront_domain_name" {
  description = "CloudFront domain — create a CNAME record for frontend_domain pointing here"
  value       = module.cloudfront.cloudfront_domain_name
}

output "ecr_repository_url" {
  description = "ECR repository URL for Docker push"
  value       = module.ecr.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "media_bucket_name" {
  description = "S3 media bucket name"
  value       = module.s3.media_bucket_name
}

output "frontend_bucket_name" {
  description = "S3 frontend bucket name"
  value       = module.s3.frontend_bucket_name
}

output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC — use as GH_DEPLOY_ROLE_ARN secret"
  value       = module.iam.github_actions_role_arn
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.rds.db_endpoint
  sensitive   = true
}
