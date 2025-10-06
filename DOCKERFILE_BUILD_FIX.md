# Dockerfile Build Failure Fix

## Problem: Build Fails During `pip install`

**Symptoms:**
```
#10 9.343 Downloading language_data-1.3.0-py3-none-any.whl (5.4 MB)
Deployment failed. Removing the new version of your application.
Gracefully shutting down build container
```

**Root Cause:** 
- Build timing out during dependency installation
- Network timeout downloading large packages (especially spaCy and dependencies)
- Coolify build timeout (default ~10 minutes)

---

## Solution Applied

### 1. **Optimized Dockerfile** ✅

**Changes made:**
- Split `pip install` into multiple RUN commands (better layer caching)
- Added `--timeout=300` (5 minutes per package)
- Added `--retries=5` (retry on network failures)
- Grouped related packages together
- Install heavy packages (spaCy, PyMuPDF) separately

**Before:**
```dockerfile
RUN pip install --no-cache-dir --user -r requirements.txt
```

**After:**
```dockerfile
RUN pip install --no-cache-dir --user --timeout=300 --retries=5 \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-dotenv==1.0.0 \
    pydantic \
    && pip install --no-cache-dir --user --timeout=300 --retries=5 \
    sqlalchemy[asyncio]==2.0.23 \
    aiosqlite==0.19.0 \
    alembic==1.12.1
# ... etc
```

**Benefits:**
- Each package group has its own timeout
- Failed downloads are retried automatically
- Better layer caching (rebuild is faster if one group fails)

### 2. **Added `.dockerignore`** ✅

Excludes unnecessary files from Docker context:
```
__pycache__/
.git/
tests/
*.md
.env
dev.db
```

**Benefits:**
- Faster build (smaller context)
- No sensitive files in image

### 3. **Alternative Dockerfile** ✅

Created `Dockerfile.optimized` with even more granular package installation.

**To use it in Coolify:**
1. Rename current `Dockerfile` → `Dockerfile.old`
2. Rename `Dockerfile.optimized` → `Dockerfile`
3. Commit and push
4. Redeploy

---

## Deployment Steps

### Option A: Use Updated Dockerfile (Recommended)

The main `Dockerfile` has been updated with timeouts and retries:

```bash
# Commit changes
git add Dockerfile .dockerignore
git commit -m "Optimize Dockerfile to fix build timeouts"
git push

# Redeploy in Coolify
```

### Option B: Use Highly Optimized Dockerfile

If Option A still fails, switch to the alternative:

```bash
# Use the highly optimized version
mv Dockerfile Dockerfile.old
mv Dockerfile.optimized Dockerfile

git add Dockerfile
git commit -m "Switch to optimized Dockerfile with granular package installation"
git push

# Redeploy in Coolify
```

---

## Testing Locally

Before deploying, test the Docker build locally:

```powershell
# Build with the updated Dockerfile
docker build -t promopack-test .

# If that fails, try the optimized version
docker build -f Dockerfile.optimized -t promopack-test .

# If build succeeds, test run
docker run -p 8000:8000 `
  -e API_KEY_SECRET=test `
  -e LANGEXTRACT_API_KEY=your-key `
  -e ENV=prod `
  promopack-test

# Test health endpoint
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
```

---

## Monitoring Build Progress in Coolify

1. **Watch Build Logs in Real-Time**
   - Click on your application
   - Go to "Logs" → "Build Logs"
   - Watch for progress through each RUN command

2. **Identify Which Package Fails**
   - Each `pip install` group is separate
   - If build fails, note which package group was installing
   - You can further split that group

3. **Check Build Time**
   - If build takes >10 minutes, it might timeout
   - Consider increasing Coolify build timeout (if possible)
   - Or further optimize Dockerfile

---

## Expected Build Output

Successful build should show:

```
Step 7/15 : RUN pip install --no-cache-dir --user --timeout=300 --retries=5     fastapi==0.104.1     uvicorn[standard]==0.24.0 ...
 ---> Running in abc123...
Collecting fastapi==0.104.1
  Downloading fastapi-0.104.1-py3-none-any.whl (92 kB)
...
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 ...

Step 8/15 : RUN pip install --no-cache-dir --user --timeout=300 --retries=5     sqlalchemy[asyncio]==2.0.23 ...
 ---> Running in def456...
...
Successfully installed sqlalchemy-2.0.23 ...

# ... continue through all package groups ...

Step 11/15 : RUN pip install --no-cache-dir --user --timeout=300 --retries=5     spacy==3.7.2
 ---> Running in ghi789...
Collecting spacy==3.7.2
  Downloading spacy-3.7.2.tar.gz (... MB)
...
Successfully installed spacy-3.7.2

Step 12/15 : RUN pip install --no-cache-dir --user --timeout=300 --retries=5     https://github.com/...en_core_web_sm-3.7.1...
 ---> Running in jkl012...
Successfully installed en-core-web-sm-3.7.1

# ... remaining steps ...

Successfully built abc123def456
Successfully tagged your-image:latest
```

---

## If Build Still Fails

### 1. Increase Timeout Values

Edit Dockerfile to increase timeout:
```dockerfile
RUN pip install --no-cache-dir --user --timeout=600 --retries=10 \
    spacy==3.7.2
```

### 2. Use Pre-built Wheels

For large packages like spaCy, consider using pre-built wheels from PyPI instead of building from source.

### 3. Multi-stage Build

Consider a multi-stage build that pre-installs dependencies:

```dockerfile
# Stage 1: Build dependencies
FROM python:3.13-slim as builder
# Install all dependencies here

# Stage 2: Runtime
FROM python:3.13-slim
COPY --from=builder /app/.local /app/.local
# Copy only what's needed
```

### 4. Check Coolify Build Settings

In Coolify:
- Increase build timeout (Settings → Build Timeout)
- Check available resources (CPU/RAM during build)
- Enable build caching if available

---

## Alternative: Use Pre-built Docker Image

If builds continue to fail, consider:

1. **Build locally and push to Docker Hub:**
   ```bash
   docker build -t yourusername/promopack-extractor:latest .
   docker push yourusername/promopack-extractor:latest
   ```

2. **Configure Coolify to use the pre-built image**
   - Instead of building from Dockerfile
   - Pull from Docker Hub

---

## Changes Committed

Files modified:
- ✅ `Dockerfile` - Added timeouts, retries, split packages
- ✅ `.dockerignore` - Exclude unnecessary files
- ✅ `Dockerfile.optimized` - Alternative with even more granular installation
- ✅ `DOCKERFILE_BUILD_FIX.md` - This documentation

**Next Steps:**
1. Push these changes to GitHub
2. Redeploy in Coolify
3. Monitor build logs
4. If successful, app should start and `/health` should return 200 OK
