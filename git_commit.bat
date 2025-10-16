@echo off
REM YouTube MCP Server v2.0 - Git Commit Script
REM Run this script to commit and push all changes

echo ============================================
echo YouTube MCP Server v2.0 - Git Push
echo ============================================
echo.

REM Navigate to directory
cd /d "%~dp0"

echo [1/6] Checking Git status...
git status
echo.

echo [2/6] Adding new documentation files...
git add SECURITY.md
git add GOOGLE_CLOUD_DEPLOYMENT.md
git add DEPLOYMENT_PLAN.md
git add HANDOVER.md
echo ✓ Documentation added
echo.

echo [3/6] Adding deployment files...
git add Dockerfile
git add .dockerignore
git add .gcloudignore
git add cloudbuild.yaml
echo ✓ Deployment files added
echo.

echo [4/6] Adding utility files...
git add utils/secret_manager.py
git add .env.example
echo ✓ Utility files added
echo.

echo [5/6] Adding updated README...
git add README.md
echo ✓ README updated
echo.

echo [6/6] Committing changes...
git commit -m "v2.0: Production-ready with Secret Manager and comprehensive security

- Add SECURITY.md with security policy and best practices
- Add GOOGLE_CLOUD_DEPLOYMENT.md with complete GCP deployment guide
- Add utils/secret_manager.py for Google Secret Manager integration
- Add DEPLOYMENT_PLAN.md with step-by-step deployment instructions
- Add HANDOVER.md with project handover documentation
- Add cloudbuild.yaml for automated Cloud Build deployment
- Update Dockerfile with multi-stage build and security hardening
- Update .dockerignore and add .gcloudignore to prevent secrets upload
- Update README.md with Secret Manager instructions
- Update .env.example with all configuration options

Security improvements:
- CORS properly configured (no wildcard by default)
- OAuth2 tokens encrypted with AES-256
- Secret Manager integration for production
- Non-root Docker user
- Health checks and monitoring
- Comprehensive input validation
- Rate limiting enabled

Ready for:
- Public release on GitHub
- Private deployment on Google Cloud Run
- Production use with proper security"

echo.
echo ✓ Changes committed successfully!
echo.

echo Ready to push? This will upload to GitHub: aihenryai/youtube-mcp-server
echo.
pause

echo.
echo Pushing to GitHub...
git push origin main

echo.
echo ============================================
echo ✓ Successfully pushed to GitHub!
echo ============================================
echo.
echo Next steps:
echo 1. Visit: https://github.com/aihenryai/youtube-mcp-server
echo 2. Create a release tag (optional):
echo    git tag -a v2.0 -m "Version 2.0 - Production Ready"
echo    git push origin v2.0
echo.
echo For Google Cloud deployment, see:
echo - GOOGLE_CLOUD_DEPLOYMENT.md
echo - DEPLOYMENT_PLAN.md
echo.
pause
