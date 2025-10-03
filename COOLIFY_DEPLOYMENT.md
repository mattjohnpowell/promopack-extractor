# Coolify Deployment Guide for PromoPack Extractor

## Prerequisites
- Coolify instance running on your VPS
- GitHub repository with your code pushed
- Production API keys ready

## Step 1: Create GitHub Repository
1. Go to https://github.com and sign in
2. Click "New repository"
3. Name: `promopack-extractor` (or your preferred name)
4. Make it public or private
5. Don't initialize with README (we already have one)
6. Click "Create repository"

## Step 2: Push Code to GitHub
After creating the repo, run these commands in your terminal:

```bash
# Add the remote (replace with your actual repo URL)
git remote add origin https://github.com/YOUR_USERNAME/promopack-extractor.git

# Push your code
git push -u origin master
```

## Step 3: Coolify Setup
1. **Access Coolify Dashboard**
   - Go to your Coolify instance URL
   - Sign in with your credentials

2. **Create New Project**
   - Click "Add Project"
   - Choose "From Git Repository"
   - Select GitHub as the provider
   - Authorize Coolify to access your GitHub account

3. **Configure the Application**
   - **Repository**: Select your `promopack-extractor` repository
   - **Branch**: `master` (or `main` if you renamed it)
   - **Build Pack**: Select "Docker" (since we have a Dockerfile)
   - **Port**: `8000` (matches our EXPOSE in Dockerfile)

4. **Environment Variables**
   Add these environment variables in Coolify:

   ```
   API_KEY_SECRET=your-production-api-key-here
   LANGEXTRACT_API_KEY=your-production-langextract-key-here
   ENV=prod
   LOG_TO_FILE=false
   LOG_LEVEL=INFO
   DATABASE_URL=sqlite:///./prod.db
   RATE_LIMIT_REQUESTS=10
   RATE_LIMIT_WINDOW=60
   MAX_FILE_SIZE=20971520
   MAX_PAGES=1000
   REQUEST_TIMEOUT=30.0
   ```

5. **Deploy**
   - Click "Deploy"
   - Coolify will build your Docker image and deploy it
   - Monitor the build logs for any issues

## Step 4: Post-Deployment Configuration

1. **Health Check**
   - Once deployed, check your app's health endpoint
   - URL: `https://your-coolify-domain.com/health`

2. **API Documentation**
   - Access Swagger docs: `https://your-coolify-domain.com/docs`
   - Access ReDoc: `https://your-coolify-domain.com/redoc`

3. **Domain Configuration** (Optional)
   - In Coolify, configure a custom domain if desired
   - Update DNS records to point to your Coolify instance

## Step 5: Testing Production Deployment

Test your API endpoints:

```bash
# Test health check
curl https://your-domain.com/health

# Test API with your production key
curl -X POST "https://your-domain.com/extract-claims" \
  -H "Authorization: Bearer your-production-api-key" \
  -H "Content-Type: application/json" \
  -d '{"document_url": "https://example.com/test.pdf"}'
```

## Troubleshooting

- **Build Failures**: Check Coolify logs for Docker build errors
- **Port Issues**: Ensure port 8000 is correctly configured
- **Environment Variables**: Verify all required variables are set
- **API Keys**: Ensure production API keys are valid and have proper permissions

## Security Notes

- Never commit `.env` files to Git
- Use strong, unique API keys for production
- Regularly rotate your API keys
- Monitor your Coolify instance for security updates

## Scaling (Future)

When you need to scale:
- Consider upgrading to PostgreSQL for the database
- Add Redis for caching
- Configure load balancing in Coolify
- Monitor performance metrics