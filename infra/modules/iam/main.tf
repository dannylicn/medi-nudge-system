variable "environment"          { type = string }
variable "aws_region"           { type = string }
variable "aws_account_id"       { type = string }
variable "media_bucket_arn"     { type = string }
variable "frontend_bucket_arn"  { type = string }
variable "github_org"           { type = string }
variable "github_repo"          { type = string }
variable "ecr_repo_arn"         { type = string }
variable "ecs_cluster_arn"      { type = string }

# ── GitHub Actions OIDC ───────────────────────────────────────────────────────

data "aws_iam_openid_connect_provider" "github" {
  count = 0 # Set to 1 after running: aws iam create-open-id-connect-provider
  url   = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1", "1c58a3a8518e8759bf075b76b750d4f2df264fcd"]
}

resource "aws_iam_role" "github_actions" {
  name = "medi-nudge-${var.environment}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Restrict to pushes to main branch only
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_actions" {
  role = aws_iam_role.github_actions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRAuth"
        Effect = "Allow"
        Action = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "ECRPush"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
        ]
        Resource = var.ecr_repo_arn
      },
      {
        Sid    = "ECSUpdateService"
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
        ]
        Resource = "*"
        Condition = {
          ArnLike = { "ecs:cluster" = var.ecs_cluster_arn }
        }
      },
      {
        Sid    = "ECSRunTask"
        Effect = "Allow"
        Action = ["ecs:RunTask", "ecs:DescribeTasks"]
        Resource = "*"
      },
      {
        Sid    = "PassTaskRoles"
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_task.arn,
          aws_iam_role.ecs_execution.arn,
        ]
      },
      {
        Sid    = "FrontendS3Sync"
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          var.frontend_bucket_arn,
          "${var.frontend_bucket_arn}/*",
        ]
      },
      {
        Sid    = "CloudFrontInvalidation"
        Effect = "Allow"
        Action = ["cloudfront:CreateInvalidation"]
        Resource = "*"
      },
    ]
  })
}

# ── ECS Task Role (runtime permissions for application code) ─────────────────

resource "aws_iam_role" "ecs_task" {
  name = "medi-nudge-${var.environment}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task" {
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "MediaS3ReadWrite"
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        Resource = "${var.media_bucket_arn}/*"
      },
      {
        Sid      = "MediaS3List"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = var.media_bucket_arn
      },
      {
        Sid    = "SecretsRead"
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:/medi-nudge/${var.environment}/*"
      },
    ]
  })
}

# ── ECS Execution Role (ECS agent permissions) ────────────────────────────────

resource "aws_iam_role" "ecs_execution" {
  name = "medi-nudge-${var.environment}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  role = aws_iam_role.ecs_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "SecretsForTaskInjection"
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:/medi-nudge/${var.environment}/*"
    }]
  })
}

output "github_actions_role_arn"  { value = aws_iam_role.github_actions.arn }
output "ecs_task_role_arn"        { value = aws_iam_role.ecs_task.arn }
output "ecs_execution_role_arn"   { value = aws_iam_role.ecs_execution.arn }
