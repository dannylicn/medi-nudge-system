variable "environment" { type = string }
variable "aws_region"  { type = string }

resource "aws_kms_key" "media" {
  description             = "medi-nudge ${var.environment} media S3 encryption"
  deletion_window_in_days = 14
  enable_key_rotation     = true
}

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
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.media.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    id     = "expire-noncurrent"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration { noncurrent_days = 90 }
  }
}

# Enforce TLS-only access
resource "aws_s3_bucket_policy" "media" {
  bucket = aws_s3_bucket.media.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = ["${aws_s3_bucket.media.arn}", "${aws_s3_bucket.media.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
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
  }
}

output "media_bucket_name"              { value = aws_s3_bucket.media.id }
output "media_bucket_arn"               { value = aws_s3_bucket.media.arn }
output "media_kms_key_arn"              { value = aws_kms_key.media.arn }
output "frontend_bucket_name"           { value = aws_s3_bucket.frontend.id }
output "frontend_bucket_arn"            { value = aws_s3_bucket.frontend.arn }
output "frontend_bucket_id"             { value = aws_s3_bucket.frontend.id }
output "frontend_bucket_regional_domain" { value = aws_s3_bucket.frontend.bucket_regional_domain_name }
