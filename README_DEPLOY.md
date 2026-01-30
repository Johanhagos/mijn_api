Deployment notes (quick)

- Local prod build:

```powershell
# Build API image
docker build -f Dockerfile.prod -t mijn_api:prod .
# Start stack
docker-compose -f docker-compose.prod.yml up -d --build
```

- Lambda packaging (if prefer serverless): use `mangum` and create a ZIP with dependencies installed into `package/` directory.

- Terraform: edit `terraform/variables.tf`, run `terraform init` and `terraform apply` in `terraform/`.

Security reminders:
- Store secrets in AWS Secrets Manager and reference in ECS task definitions.
- Use HTTPS (ACM) and CloudFront in front of ALB for production.
