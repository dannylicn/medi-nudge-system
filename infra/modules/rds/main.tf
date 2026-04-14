variable "environment"        { type = string }
variable "vpc_id"             { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "public_subnet_ids"  { type = list(string) }
variable "ecs_sg_id"          { type = string }
variable "db_instance_class"  { type = string }
variable "db_multi_az"        { type = bool }

resource "random_password" "db" {
  length           = 32
  special          = true
  override_special = "!#$%&*-_=+?"
}

resource "aws_secretsmanager_secret" "db_password" {
  name                    = "/medi-nudge/${var.environment}/db-password"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db.result
}

resource "aws_db_subnet_group" "main" {
  name       = "medi-nudge-${var.environment}"
  subnet_ids = concat(var.private_subnet_ids, var.public_subnet_ids)
  tags       = { Name = "medi-nudge-${var.environment}-db-subnet-group" }
}

resource "aws_security_group" "rds" {
  name        = "medi-nudge-${var.environment}-rds"
  description = "RDS PostgreSQL - ingress from ECS only"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.ecs_sg_id]
  }

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_kms_key" "rds" {
  description             = "medi-nudge ${var.environment} RDS encryption key"
  deletion_window_in_days = 14
  enable_key_rotation     = true
}

resource "aws_db_instance" "main" {
  identifier              = "medi-nudge-${var.environment}"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = var.db_instance_class
  allocated_storage       = 20
  max_allocated_storage   = 100
  storage_type            = "gp3"
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.rds.arn
  db_name                 = "medinudge"
  username                = "medinudge"
  password                = random_password.db.result
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  multi_az                = var.db_multi_az
  publicly_accessible     = true
  skip_final_snapshot     = false
  final_snapshot_identifier = "medi-nudge-${var.environment}-final"
  backup_retention_period = 0
  deletion_protection     = true

  tags = { Name = "medi-nudge-${var.environment}" }
}

# Build the full connection URL and store it as a secret for ECS injection
resource "aws_secretsmanager_secret" "db_url" {
  name                    = "/medi-nudge/${var.environment}/database-url"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "db_url" {
  secret_id     = aws_secretsmanager_secret.db_url.id
  secret_string = "postgresql+psycopg2://medinudge:${random_password.db.result}@${aws_db_instance.main.address}:5432/medinudge"
}

output "db_endpoint"  { value = aws_db_instance.main.address }
output "db_secret_arn" { value = aws_secretsmanager_secret.db_url.arn }
output "rds_sg_id"    { value = aws_security_group.rds.id }
