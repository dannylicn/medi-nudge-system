variable "environment" { type = string }
variable "aws_region"  { type = string }

# ── Media bucket (prescription images) ───────────────────────────────────────

resource "aws_s3_bucket" "media" {
  bucket = "medi-nudge-media-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
    bucket_key_enabled = true
  }
}

# ── Frontend bucket (React SPA) ───────────────────────────────────────────────

resource "aws_s3_bucket" "frontend" {
  bucket = "medi-nudge-frontend-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
    bucket_key_enabled = true
  }
}

output "media_bucket_name"              { value = aws_s3_bucket.media.id }
output "media_bucket_arn"               { value = aws_s3_bucket.media.arn }
output "frontend_bucket_name"           { value = aws_s3_bucket.frontend.id }
output "frontend_bucket_arn"            { value = aws_s3_bucket.frontend.arn }
output "frontend_bucket_id"             { value = aws_s3_bucket.frontend.id }
output "frontend_bucket_regional_domain" { value = aws_s3_bucket.frontend.bucket_regional_domain_name }
