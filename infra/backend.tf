# Terraform remote state backend
# Usage:
#   terraform init \
#     -backend-config="bucket=medi-nudge-tfstate-<env>" \
#     -backend-config="key=<env>/terraform.tfstate" \
#     -backend-config="region=ap-southeast-1" \
#     -backend-config="dynamodb_table=medi-nudge-tfstate-lock"
#
# Bootstrap (one-time, run manually):
#   aws s3api create-bucket --bucket medi-nudge-tfstate-<env> --region ap-southeast-1 \
#     --create-bucket-configuration LocationConstraint=ap-southeast-1
#   aws s3api put-bucket-versioning --bucket medi-nudge-tfstate-<env> \
#     --versioning-configuration Status=Enabled
#   aws s3api put-bucket-encryption --bucket medi-nudge-tfstate-<env> \
#     --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
#   aws dynamodb create-table --table-name medi-nudge-tfstate-lock \
#     --attribute-definitions AttributeName=LockID,AttributeType=S \
#     --key-schema AttributeName=LockID,KeyType=HASH \
#     --billing-mode PAY_PER_REQUEST \
#     --region ap-southeast-1
