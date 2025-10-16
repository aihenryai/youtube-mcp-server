# Google Cloud Deployment Guide 🚀

## Prerequisites

- Google Cloud account with billing enabled
- gcloud CLI installed and configured
- Docker installed locally (for testing)
- YouTube Data API key

## Initial Setup

### 1. Create Google Cloud Project

```bash
# Set your project ID
export PROJECT_ID="youtube-mcp-server"
export REGION="us-central1"

# Create project
gcloud projects create $PROJECT_ID --name="YouTube MCP Server"

# Set as active project
gcloud config set project $PROJECT_ID

# Enable billing (required for Cloud Run)
# Visit: https://console.cloud.google.com/billing
```

### 2. Enable Required APIs

```bash
# Enable necessary Google Cloud APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  containerregistry.googleapis.com \
  youtube.googleapis.com
```

### 3. Set Up Secret Manager

#### Store YouTube API Key
```bash
# Create secret for YouTube API key
echo -n "YOUR_YOUTUBE_API_KEY" | \
  gcloud secrets create youtube-api-key \
  --data-file=- \
  --replication-policy="automatic"

# Verify secret created
gcloud secrets describe youtube-api-key
```

#### Store Server API Key (for HTTP authentication)
```bash
# Generate secure random key
export SERVER_KEY=$(openssl rand -base64 32)

# Store it
echo -n "$SERVER_KEY" | \
  gcloud secrets create server-api-key \
  --data-file=- \
  --replication-policy="automatic"

# Save the key locally (you'll need it for client)
echo "SERVER_API_KEY=$SERVER_KEY" >> .env.production.local
```

#### Store OAuth2 Credentials (Optional - for write operations)
```bash
# If using OAuth2 for playlist management
gcloud secrets create oauth2-credentials \
  --data-file=credentials.json \
  --replication-policy="automatic"

# Store encrypted token (after first auth)
gcloud secrets create oauth2-token \
  --data-file=token.json \
  --replication-policy="automatic"
```

### 4. Create Service Account

```bash
# Create service account with minimal permissions
gcloud iam service-accounts create youtube-mcp-sa \
  --display-name="YouTube MCP Server Service Account"

# Grant Secret Manager access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:youtube-mcp-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Grant Cloud Run invoker role (for internal services)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:youtube-mcp-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## Deployment Options

### Option 1: Cloud Build (Recommended)

#### Create cloudbuild.yaml
```yaml
# cloudbuild.yaml
steps:
  # Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/youtube-mcp:$SHORT_SHA'
      - '-t'
      - 'gcr.io/$PROJECT_ID/youtube-mcp:latest'
      - '.'
  
  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - 'gcr.io/$PROJECT_ID/youtube-mcp:$SHORT_SHA'
  
  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'youtube-mcp'
      - '--image=gcr.io/$PROJECT_ID/youtube-mcp:$SHORT_SHA'
      - '--platform=managed'
      - '--region=$_REGION'
      - '--no-allow-unauthenticated'
      - '--service-account=youtube-mcp-sa@$PROJECT_ID.iam.gserviceaccount.com'
      - '--set-secrets=YOUTUBE_API_KEY=youtube-api-key:latest,SERVER_API_KEY=server-api-key:latest'
      - '--set-env-vars=MCP_TRANSPORT=http,CACHE_ENABLED=true,RATE_LIMIT_ENABLED=true'
      - '--max-instances=3'
      - '--min-instances=0'
      - '--memory=512Mi'
      - '--cpu=1'
      - '--timeout=300'

substitutions:
  _REGION: us-central1

images:
  - 'gcr.io/$PROJECT_ID/youtube-mcp:$SHORT_SHA'
  - 'gcr.io/$PROJECT_ID/youtube-mcp:latest'
```

#### Deploy
```bash
# Submit build
gcloud builds submit --config cloudbuild.yaml
```

### Option 2: Manual Deployment

```bash
# Build locally
docker build -t gcr.io/$PROJECT_ID/youtube-mcp:latest .

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/youtube-mcp:latest

# Deploy to Cloud Run
gcloud run deploy youtube-mcp \
  --image gcr.io/$PROJECT_ID/youtube-mcp:latest \
  --platform managed \
  --region $REGION \
  --no-allow-unauthenticated \
  --service-account youtube-mcp-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-secrets "YOUTUBE_API_KEY=youtube-api-key:latest,SERVER_API_KEY=server-api-key:latest" \
  --set-env-vars "MCP_TRANSPORT=http,CACHE_ENABLED=true,RATE_LIMIT_ENABLED=true,ALLOWED_ORIGINS=https://your-frontend.com" \
  --max-instances 3 \
  --min-instances 0 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --port 8080
```

## Security Configuration

### 1. Configure CORS

```bash
# Update deployment with allowed origins
gcloud run services update youtube-mcp \
  --region $REGION \
  --update-env-vars "ALLOWED_ORIGINS=https://your-app.com,https://your-other-app.com"
```

### 2. Enable Cloud Armor (DDoS Protection)

```bash
# Create security policy
gcloud compute security-policies create youtube-mcp-policy \
  --description "Security policy for YouTube MCP"

# Add rate limiting rule
gcloud compute security-policies rules create 1000 \
  --security-policy youtube-mcp-policy \
  --expression "true" \
  --action "rate-based-ban" \
  --rate-limit-threshold-count 100 \
  --rate-limit-threshold-interval-sec 60 \
  --ban-duration-sec 600

# Apply to Cloud Run (requires Load Balancer)
# See: https://cloud.google.com/armor/docs/configure-security-policies
```

### 3. Set Up Monitoring

```bash
# Create uptime check
gcloud monitoring uptime create youtube-mcp-check \
  --resource-type=cloud-run-revision \
  --resource-labels=service_name=youtube-mcp,location=$REGION

# Create alert policy
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="YouTube MCP High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-expression="resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
```

## Using the Deployed Service

### Get Service URL
```bash
export SERVICE_URL=$(gcloud run services describe youtube-mcp \
  --region $REGION \
  --format 'value(status.url)')

echo "Service URL: $SERVICE_URL"
```

### Test the Service

```bash
# Get authentication token
export TOKEN=$(gcloud auth print-identity-token)

# Test health endpoint
curl -H "Authorization: Bearer $TOKEN" \
  $SERVICE_URL/health

# Test with MCP client
curl -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"method":"get_video_info","params":{"video_url":"dQw4w9WgXcQ"}}' \
  $SERVICE_URL/mcp
```

### Connect Claude Desktop

#### Using Cloud Run Proxy (Recommended)
```bash
# Run proxy (keeps authentication)
gcloud run services proxy youtube-mcp --region $REGION --port 3000
```

Update `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "youtube-cloud": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:3000/sse"]
    }
  }
}
```

#### Using Direct Connection (Advanced)
```json
{
  "mcpServers": {
    "youtube-cloud": {
      "command": "gcloud",
      "args": [
        "run",
        "services",
        "proxy",
        "youtube-mcp",
        "--region=us-central1",
        "--port=3000"
      ]
    }
  }
}
```

## Cost Optimization

### 1. Set Resource Limits
```bash
gcloud run services update youtube-mcp \
  --region $REGION \
  --memory 256Mi \          # Reduce if possible
  --cpu 1 \                 # Minimum CPU
  --max-instances 3 \       # Prevent runaway costs
  --min-instances 0 \       # Scale to zero
  --concurrency 80          # Requests per instance
```

### 2. Enable Request Timeout
```bash
gcloud run services update youtube-mcp \
  --region $REGION \
  --timeout 60              # Max 60 seconds per request
```

### 3. Monitor Costs
```bash
# Set budget alert
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="YouTube MCP Budget" \
  --budget-amount=10.00 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

## Estimated Costs (US Region)

**Cloud Run** (pay-per-use):
- First 2 million requests/month: FREE
- Memory: $0.0000025/GB-second
- CPU: $0.00002400/vCPU-second

**Estimated Monthly Cost** (light usage):
- 100,000 requests/month
- Avg 200ms response time
- 256MB memory
- **Total: ~$0.50-2.00/month**

**Secret Manager**:
- First 6 secrets: FREE
- Access operations: $0.03/10,000 operations
- **Total: FREE (for this project)**

**Container Registry**:
- Storage: $0.026/GB/month
- ~500MB image size
- **Total: ~$0.01/month**

**Total Estimated: $0.51-2.01/month**

## Troubleshooting

### View Logs
```bash
# Recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=youtube-mcp" \
  --limit 50 \
  --format json

# Follow logs in real-time
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=youtube-mcp"
```

### Debug Container
```bash
# Get shell in running container (development only)
gcloud run services exec youtube-mcp \
  --region $REGION \
  -- /bin/bash
```

### Check Secrets Access
```bash
# Verify service account can access secrets
gcloud secrets describe youtube-api-key \
  --format="value(name)"

# Test secret value (careful!)
gcloud secrets versions access latest \
  --secret=youtube-api-key
```

## Cleanup

```bash
# Delete Cloud Run service
gcloud run services delete youtube-mcp --region $REGION

# Delete secrets
gcloud secrets delete youtube-api-key
gcloud secrets delete server-api-key

# Delete service account
gcloud iam service-accounts delete youtube-mcp-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Delete project (if desired)
gcloud projects delete $PROJECT_ID
```

## Production Checklist

Before going to production:

- [ ] API keys stored in Secret Manager
- [ ] CORS configured (no "*")
- [ ] Service account with minimal permissions
- [ ] Authentication enabled (IAM or API key)
- [ ] Rate limiting enabled
- [ ] Monitoring and alerts configured
- [ ] Budget alerts set up
- [ ] Logs reviewed and working
- [ ] Health check passing
- [ ] Resource limits set
- [ ] Backup secrets securely
- [ ] Document service URL and keys

## Support

For issues:
- Check logs: `gcloud logging read`
- Review quotas: https://console.cloud.google.com/iam-admin/quotas
- Support: https://cloud.google.com/support

---

**Security Note**: Never commit credentials to Git. Always use Secret Manager for production secrets.
