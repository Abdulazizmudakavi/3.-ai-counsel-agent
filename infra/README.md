# AWS setup (Mumbai, ap-south-1)

Done by a person with company billing access — not automated here. Terraform follows once the
account exists.

1. **Account**: create (or get) an AWS account under the company; enable MFA on root, then use
   IAM Identity Center users only. Set the default region to `ap-south-1`.
2. **Bedrock India access**: in the Bedrock console (ap-south-1) request access to the Anthropic
   models. Then list what the India endpoint serves:
   ```powershell
   aws bedrock list-foundation-models --region ap-south-1 --by-provider anthropic --query "modelSummaries[].modelId"
   aws bedrock list-inference-profiles --region ap-south-1
   ```
   Record the model / inference-profile IDs in `.env` (`COUNSEL_MODEL_*`). If 5.5 models are not
   listed, use what is and tell Sana and Arina (team plan risk table). Confirm in-country inference
   and zero data retention **in writing** — due end of week 2.
3. **Postgres**: RDS for PostgreSQL 16 with the `vector` extension, encrypted with a KMS key,
   private subnets only.
4. **Object storage**: S3 bucket for files (SSE-KMS); a second bucket with **Object Lock** for
   write-once audit exports.
5. **Secrets**: AWS Secrets Manager for DB credentials and mail tokens; nothing in code or logs.
6. **Budget alarm** on the account before anything runs.
