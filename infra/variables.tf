variable "aws_region" {
  description = "Primary AWS region"
  type        = string
  default     = "ap-southeast-1"
}

variable "environment" {
  description = "Deployment environment (staging | production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be 'staging' or 'production'."
  }
}

variable "app_domain" {
  description = "Base domain (optional — leave empty to use auto-generated AWS DNS names)"
  type        = string
  default     = ""
}

variable "api_domain" {
  description = "API subdomain (optional — leave empty to use ALB DNS name)"
  type        = string
  default     = ""
}

variable "frontend_domain" {
  description = "Frontend subdomain (optional — leave empty to use CloudFront *.cloudfront.net domain)"
  type        = string
  default     = ""
}

variable "github_org" {
  description = "GitHub organisation or username owning the repository"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name (without org prefix)"
  type        = string
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.small"
}

variable "db_multi_az" {
  description = "Enable RDS Multi-AZ"
  type        = bool
  default     = false
}

variable "ecs_api_desired_count" {
  description = "Desired ECS task count for the API service"
  type        = number
  default     = 1
}

variable "acm_certificate_arn_apigw" {
  description = "ARN of the ACM certificate in ap-southeast-1 for the ALB (optional — required only when api_domain is set)"
  type        = string
  default     = ""
}

variable "acm_certificate_arn_cloudfront" {
  description = "ARN of the ACM certificate in us-east-1 for CloudFront (optional — required only when frontend_domain is set)"
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Route 53 hosted zone ID for the app domain (optional — when set, DNS records for api_domain and frontend_domain are created automatically)"
  type        = string
  default     = ""
}
