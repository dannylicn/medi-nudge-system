# Medi-Nudge Teardown Checklist

Everything to clean up after the hackathon (by 2026-05-25).

## 1. Terraform-managed resources

Run from `infra/` directory:

```bash
terraform destroy -var-file=environments/staging/terraform.tfvars
```

This destroys:

- VPC (nova-vpc) + subnets, IGW, route tables
- ECS cluster (medi-nudge-staging) + services + task definitions
- ECR repository (medi-nudge-api)
- ALB (medi-nudge-staging) + target group + security groups
- RDS instance (medi-nudge-staging)
- S3 buckets (medi-nudge-media-staging, medi-nudge-frontend-staging)
- CloudFront distribution
- IAM roles (ECS task, execution, GitHub Actions OIDC)
- Secrets Manager: database-url, db-password (created by Terraform)
- Security groups (ECS, RDS, ALB)

## 2. Manually created AWS resources

Delete via console or CLI after `terraform destroy`:

| Resource | Name |
|----------|------|
| S3 bucket (TF state) | medi-nudge-tfstate-gt |
| DynamoDB table (TF lock) | medi-nudge-tfstate-lock |
| Secrets Manager | /medi-nudge/staging/jwt-secret-key |
| | /medi-nudge/staging/openai-api-key |
| | /medi-nudge/staging/telegram-bot-token |
| | /medi-nudge/staging/telegram-webhook-secret |
| | /medi-nudge/staging/telegram-bot-username |
| | /medi-nudge/staging/elevenlabs-api-key |
| | /medi-nudge/staging/elevenlabs-default-voice-female |
| | /medi-nudge/staging/elevenlabs-default-voice-male |
| | /medi-nudge/staging/allowed-origins |

Note: Secrets Manager has a 7-day recovery window. To delete immediately, use `--force-delete-without-recovery` flag.

## 3. External accounts/services

| Service | What to do |
|---------|-----------|
| Telegram bot (@MediNudgeBot) | Message @BotFather, send /deletebot |
| OpenAI | Revoke API key, remove payment method if desired |
| ElevenLabs | Revoke API key, delete account if desired |

## 4. Local cleanup

| Item | Action |
|------|--------|
| SSH key (GitHub) | Delete ~/.ssh/id_ed25519_github, remove from GitHub Settings |
| SSH config | Remove github.com entry from ~/.ssh/config |
| Docker images | Remove medi-nudge-api image from Docker Desktop |

## 5. Order of teardown

1. Run `terraform destroy`
2. Delete the 9 Secrets Manager secrets
3. Empty and delete medi-nudge-tfstate-gt S3 bucket
4. Delete medi-nudge-tfstate-lock DynamoDB table
5. Delete Telegram bot via @BotFather
6. Revoke OpenAI and ElevenLabs API keys
7. Clean up local SSH key, Docker images
