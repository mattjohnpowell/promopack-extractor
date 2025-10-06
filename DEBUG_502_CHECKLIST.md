# 502 Error Diagnosis - Step by Step

## Current Status
- ✅ Dockerfile matches working version (commit 65c6246)
- ✅ requirements.txt matches working version (no spacy)
- ✅ Code imports successfully locally
- ❌ Deployed app returns 502 Bad Gateway

---

## Step-by-Step Diagnosis

### Step 1: Check Coolify Build Logs ⚠️ CRITICAL

**Go to Coolify → Your App → Logs → Build Logs**

Look for:
```
✓ Successfully built [image-id]
✓ Successfully tagged [image-name]
```

**If you see:**
```
❌ Deployment failed. Removing the new version...
```
→ Build is failing. Check what step failed.

**Expected successful build output:**
```
Step 1/15: FROM python:3.12-slim
Step 7/15: RUN pip install --no-cache-dir --user -r requirements.txt
 ---> Running in [container-id]
Collecting fastapi==0.104.1
...
Successfully installed [all packages]
...
Step 15/15: CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
Successfully built abc123
```

---

### Step 2: Check Coolify Runtime Logs ⚠️ CRITICAL

**Go to Coolify → Your App → Logs → Runtime Logs**

**Expected startup logs:**
```json
{"timestamp": "...", "level": "INFO", "message": "Application startup complete"}
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**If you see errors:**
```python
❌ ValueError: Missing required configuration: langextract_api_key
❌ ModuleNotFoundError: No module named 'claim_validation'
❌ ImportError: cannot import name 'claim_validator'
```
→ Environment variables or code issue

---

### Step 3: Check Container Status

**In Coolify:**
- Is container status: **Running** or **Stopped**?
- Is health check: **Healthy** or **Unhealthy**?

**If Stopped:**
→ Container is crashing on startup. Check runtime logs.

**If Unhealthy:**
→ Health check failing. App might be running but not responding.

---

### Step 4: Test Health Endpoint Internally

**If Coolify has Console/Shell access:**
```bash
# From inside the container
curl http://localhost:8000/health
```

**Expected:**
```json
{"status": "healthy", "timestamp": "..."}
```

**If command not found or timeout:**
→ App isn't running or not listening on port 8000

---

### Step 5: Verify Environment Variables

**In Coolify Console:**
```bash
echo $LANGEXTRACT_API_KEY
echo $API_KEY_SECRET
echo $ENV
```

**Expected:**
```
AIzaSyAc1rCvcoVjE2S8H95ThGKWjSkyb9xqrro
test-api-key
prod
```

**If empty:**
→ Environment variables not set or not passed to container

---

### Step 6: Check Port Configuration

**In Coolify Settings:**
- Container Port: Should be `8000`
- Protocol: Should be `HTTP` (not HTTPS at container level)

**Common mistake:**
- Setting container port to 443 or 80 instead of 8000
- Setting protocol to HTTPS instead of HTTP

---

### Step 7: Run Diagnostic Script

**In Coolify Console:**
```bash
python healthcheck.py
```

**This will check:**
- ✓ Environment variables set
- ✓ Modules can import
- ✓ Claim validation loads
- ✓ Config validates
- ✓ Database initializes
- ✓ App creates successfully

---

## Common Causes & Fixes

### Cause 1: Build Still Failing (Cached Layers)
**Symptom:** Build logs show timeout or package download failure

**Fix:**
1. In Coolify, find "Clear Cache" or "Force Rebuild" option
2. OR: Delete the application and recreate it
3. OR: I can add a cache-busting ARG to Dockerfile

**Test:**
```bash
# Check if build completed
# Look for "Successfully built" in build logs
```

---

### Cause 2: Environment Variables Not Set
**Symptom:** Runtime logs show `ValueError: Missing required configuration`

**Fix:**
1. Go to Coolify → Environment Variables
2. Ensure these are set:
   ```
   API_KEY_SECRET=test-api-key
   LANGEXTRACT_API_KEY=AIzaSyAc1rCvcoVjE2S8H95ThGKWjSkyb9xqrro
   ENV=prod
   ```
3. Click "Restart" (not just Redeploy)

---

### Cause 3: App Crashes on Startup
**Symptom:** Container status shows "Stopped" or runtime logs show Python errors

**Fix:**
Check runtime logs for the exact error:
- `ModuleNotFoundError` → Build didn't install packages correctly
- `ImportError` → Code issue (claim_validation changes)
- `ValueError` → Missing environment variables

---

### Cause 4: Port Mismatch
**Symptom:** Container running but 502 persists, no errors in logs

**Fix:**
1. Verify Coolify container port is `8000`
2. Verify Dockerfile exposes port `8000` (it does)
3. Verify CMD uses port `8000` (it does)

**Test in console:**
```bash
netstat -tulpn | grep 8000
# Should show: 0.0.0.0:8000 with python/uvicorn
```

---

### Cause 5: Health Check Failing
**Symptom:** Container status "Unhealthy"

**Fix:**
Health check in Dockerfile:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

**Test manually:**
```bash
curl -f http://localhost:8000/health
echo $?  # Should be 0 (success)
```

---

### Cause 6: Coolify Proxy Configuration
**Symptom:** Everything looks good in container, but 502 from outside

**Fix:**
1. Check Coolify proxy settings
2. Verify domain is correctly configured
3. Check SSL certificate is valid
4. Look for Coolify proxy logs

---

## Quick Diagnostic Commands

### From Your Local Machine:
```powershell
# Test if domain resolves
Resolve-DnsName promopack-extractor.powellmatt.com

# Test if port is accessible (should get SSL/TLS response)
Test-NetConnection promopack-extractor.powellmatt.com -Port 443

# Test health endpoint
try {
    Invoke-WebRequest -Uri "https://promopack-extractor.powellmatt.com/health" -UseBasicParsing
} catch {
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "Error: $_"
}
```

### From Coolify Console:
```bash
# Check if app is running
ps aux | grep uvicorn

# Check if port is listening
netstat -tulpn | grep 8000

# Check environment variables
env | grep -E "API_KEY|LANGEXTRACT|ENV"

# Test health endpoint
curl -v http://localhost:8000/health

# Run full diagnostic
python healthcheck.py
```

---

## What to Share for Further Help

If the issue persists, please share:

1. **Build Logs** (last 50 lines)
   - Go to Coolify → Logs → Build Logs
   - Copy last section showing success or failure

2. **Runtime Logs** (last 50 lines)
   - Go to Coolify → Logs → Runtime Logs
   - Copy any errors or startup messages

3. **Container Status**
   - Running/Stopped/Unhealthy?

4. **Environment Variables**
   - Are they set in Coolify UI?
   - Can you verify with `echo $API_KEY_SECRET` in console?

5. **healthcheck.py Output**
   - Run `python healthcheck.py` in Coolify console
   - Share full output

6. **Port Configuration**
   - What port is configured in Coolify settings?

---

## Most Likely Issues (In Order)

Based on our troubleshooting so far:

1. **Build still using cached layers with spacy** (60%)
   - Fix: Force rebuild / clear cache in Coolify

2. **Environment variables not passed to container** (20%)
   - Fix: Verify in Coolify console with `echo $VAR`

3. **Container crashing on startup** (10%)
   - Fix: Check runtime logs for Python errors

4. **Port configuration issue** (5%)
   - Fix: Verify port 8000 in Coolify settings

5. **Coolify proxy misconfiguration** (5%)
   - Fix: Check Coolify proxy logs

---

## Next Actions

**Priority Order:**

1. ✅ **Check Build Logs** - Did build complete successfully?
2. ✅ **Check Runtime Logs** - Is app starting without errors?
3. ✅ **Check Container Status** - Is it running and healthy?
4. ✅ **Run healthcheck.py** - What does diagnostic say?
5. ✅ **Verify environment variables** - Are they set in container?

**Start with #1 and work down the list.** Share the results and I can pinpoint the exact issue!
