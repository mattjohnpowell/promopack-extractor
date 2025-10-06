# Troubleshooting 502 Bad Gateway Error

## Immediate Checks in Coolify

### 1. Check Application Logs
**In Coolify Dashboard:**
1. Navigate to your application
2. Click "Logs" → "Build Logs" to see if Docker build succeeded
3. Click "Logs" → "Runtime Logs" to see application startup errors

**Look for:**
- ❌ `ModuleNotFoundError` - Missing dependencies
- ❌ `KeyError` - Missing environment variables
- ❌ `ConnectionError` - Database connection issues
- ❌ `PermissionError` - File system permissions
- ❌ `ImportError` - Failed imports (e.g., spaCy model)
- ❌ `ValueError: Missing required configuration` - Environment variables not set properly

### 2. Run Diagnostic Script in Coolify Console

**NEW: Built-in Health Check Script**

We've added a `healthcheck.py` script that diagnoses all potential issues:

1. In Coolify, open your application's **Console/Shell**
2. Run this command:
   ```bash
   python healthcheck.py
   ```

This will check:
- ✓ Environment variables are set
- ✓ All Python modules can be imported
- ✓ spaCy model is available
- ✓ Configuration loads without errors
- ✓ Database can be initialized
- ✓ FastAPI app can be created

**Expected output if everything is OK:**
```
==================================================
DEPLOYMENT HEALTH CHECK
==================================================

Environment Variables Check:
--------------------------------------------------
✓ API_KEY_SECRET=test-api-ke...
✓ LANGEXTRACT_API_KEY=AIzaSyAc1r...
✓ ENV=prod

✓ All required environment variables are set

Module Import Check:
--------------------------------------------------
✓ fastapi
✓ uvicorn
✓ sqlalchemy
...

✓ All checks passed! App should start successfully.
```

### 3. Verify Environment Variables
**Required variables that MUST be set:**
```bash
LANGEXTRACT_API_KEY=<your-key>
API_KEY_SECRET=<your-key>
ENV=prod
```

**Check in Coolify Console:**
```bash
echo $API_KEY_SECRET
echo $LANGEXTRACT_API_KEY
echo $ENV
```

If any are empty, they're not being passed to the container properly.

### 4. Check Port Configuration
- **Container Port**: Should be `8000`
- **Public Port**: Usually auto-assigned by Coolify
- **Protocol**: HTTP (not HTTPS at container level)

### 5. Test Health Endpoint Internally
**In Coolify Shell/Console:**
```bash
curl http://localhost:8000/health
```

If this fails, your app isn't starting properly.

---

## Common Fixes

### Fix 1: Missing spaCy Model
**Problem:** The Dockerfile downloads `en_core_web_sm` but it might fail silently.

**Diagnosis:** Run in Coolify console:
```bash
python -c "import spacy; spacy.load('en_core_web_sm')"
```

**If it fails:** Check build logs for spaCy download errors during build.

### Fix 2: Environment Variable Issues
**Problem:** Missing required API keys causes startup failure.

**Diagnosis:** Run in Coolify console:
```bash
python -c "from config import config; print(f'Ready: {config.is_ready()}')"
```

**Expected:** `Ready: True`

**If False:** Environment variables aren't being set properly in Coolify.

### Fix 3: Database File Permissions
**Problem:** SQLite database file can't be created due to permissions.

**Diagnosis:** Run in Coolify console:
```bash
touch /app/test.db && echo "Permissions OK" || echo "Permissions FAIL"
rm /app/test.db
```

### Fix 4: Port Not Listening
**Problem:** App starts but doesn't listen on port 8000.

**Diagnosis:** Run in Coolify console:
```bash
# Check if anything is listening on port 8000
netstat -tulpn | grep 8000
# or
ss -tulpn | grep 8000
```

**Expected:** You should see `uvicorn` or `python` listening on `0.0.0.0:8000`

### Fix 5: App Crashes After Startup
**Problem:** App starts but crashes when handling first request.

**Diagnosis:** Watch runtime logs while making a request:
```bash
# In one terminal, tail logs
# In another, make a request to health endpoint
curl http://localhost:8000/health
```

Look for Python tracebacks in the logs.

---

## Quick Diagnostic Commands

### Test from Coolify Console:
```bash
# 1. Check Python version
python --version  # Should be 3.12.x

# 2. Check uvicorn is installed
uvicorn --version

# 3. Test import of main app
python -c "from main import app; print('App import: OK')"

# 4. Run health check script
python healthcheck.py

# 5. Check if app is running
ps aux | grep uvicorn

# 6. Check listening ports
netstat -tulpn | grep 8000
```

### Test from your local machine:
```powershell
# Health check
try {
    $response = Invoke-WebRequest -Uri "https://promopack-extractor.powellmatt.com/health" -UseBasicParsing -ErrorAction Stop
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Content: $($response.Content)"
} catch {
    Write-Host "Error: $_"
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
}
```

### Expected responses:
- **200 OK**: App is healthy ✓
- **502 Bad Gateway**: App isn't responding (container down/crashed) ✗
- **503 Service Unavailable**: Coolify can't reach the app ✗
- **404 Not Found**: App is running but endpoint doesn't exist ✗

---

## Root Cause Investigation

### Most Likely Causes (in order):

1. **Missing Environment Variables in Container** (40% probability)
   - Environment variables set in Coolify UI but not passed to container
   - **Fix:** Verify with `echo $LANGEXTRACT_API_KEY` in Coolify console
   - **Test:** Run `python healthcheck.py`

2. **spaCy model missing** (25% probability)
   - Download failed during Docker build
   - **Fix:** Check build logs, rebuild if necessary
   - **Test:** `python -c "import spacy; spacy.load('en_core_web_sm')"`

3. **Database initialization failure** (15% probability)
   - SQLite file can't be created
   - **Fix:** Check file permissions in /app directory
   - **Test:** `touch /app/test.db`

4. **Port misconfiguration** (10% probability)
   - Coolify expecting different port
   - **Fix:** Verify port 8000 in Coolify settings
   - **Test:** `netstat -tulpn | grep 8000`

5. **Import errors** (5% probability)
   - Missing dependencies in requirements.txt
   - **Fix:** Check build logs for pip install failures
   - **Test:** `python -c "import api"`

6. **Health check timeout** (5% probability)
   - App takes too long to start
   - **Fix:** Increase health check timeout in Dockerfile
   - **Test:** Watch startup time in logs

---

## Coolify-Specific Issues

### Issue: Environment Variables Not Passed to Container

**Symptom:** Variables show in Coolify UI but `echo $VAR` in console returns empty

**Fix:**
1. Click "Restart" (not just "Redeploy")
2. Ensure variables are in "Environment Variables" section, not "Secrets"
3. Check for typos in variable names (case-sensitive)

### Issue: Build Succeeds but Container Doesn't Start

**Symptom:** Build logs show "Success" but runtime logs are empty or show crash

**Fix:**
1. Check the CMD in Dockerfile: `uvicorn main:app --host 0.0.0.0 --port 8000`
2. Manually start app in console: `uvicorn main:app --host 0.0.0.0 --port 8000`
3. Watch for errors during startup

### Issue: Health Check Fails

**Symptom:** Container marked as "unhealthy" in Coolify

**The Dockerfile health check:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

**Fix:**
1. Ensure `curl` is installed (it's in the Dockerfile)
2. Increase `--start-period` if app takes longer to start
3. Check if `/health` endpoint is actually accessible

---

## Next Steps

**Priority Order:**

1. **✓ Run `python healthcheck.py` in Coolify Console** (CRITICAL)
   - This will identify the exact issue
   
2. **✓ Check Coolify Runtime Logs**
   - Look for Python tracebacks or startup errors

3. **✓ Verify Environment Variables in Console**
   ```bash
   echo $API_KEY_SECRET
   echo $LANGEXTRACT_API_KEY
   ```

4. **✓ Test App Import**
   ```bash
   python -c "from main import app; print('OK')"
   ```

5. **✓ Check if Port 8000 is Listening**
   ```bash
   netstat -tulpn | grep 8000
   ```

---

## If Still Stuck

Share the following information for further diagnosis:

- [ ] Output of `python healthcheck.py` from Coolify console
- [ ] Coolify **Runtime Logs** (last 50 lines)
- [ ] Coolify **Build Logs** (last 50 lines)  
- [ ] Output of `echo $API_KEY_SECRET` from console (can redact value)
- [ ] Container status (running/stopped/unhealthy)
- [ ] Output of `ps aux | grep uvicorn` from console

---

## Recent Fixes Applied

### 2025-10-06: Added Comprehensive Diagnostics

1. **Created `healthcheck.py`** - Standalone diagnostic script
2. **Fixed `main.py`** - Removed unused FastAPI import
3. **Verified startup event registration** - Ensure database initializes

**To apply these fixes:**
```bash
# Commit and push changes
git add healthcheck.py main.py
git commit -m "Add diagnostic healthcheck script and fix main.py"
git push

# Redeploy in Coolify
```

Then run `python healthcheck.py` in Coolify console to verify everything works.
