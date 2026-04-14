variable "environment" { type = string }

resource "aws_ecr_repository" "api" {
  name                 = "medi-nudge-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration { scan_on_push = true }

  tags = { Name = "medi-nudge-api" }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 20 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = { type = "expire" }
    }]
  })
}

output "repository_url" { value = aws_ecr_repository.api.repository_url }
output "repository_arn" { value = aws_ecr_repository.api.arn }
