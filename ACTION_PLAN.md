# 502 Error - Action Plan

## What We Know

✓ Your **local app works fine** (health endpoint returns 200 OK)  
✓ Environment variables are **set in Coolify UI**  
✗ Deployed app returns **502 Bad Gateway**  

## Root Cause Diagnosis

The 502 error means **your app container isn't responding**. Since the environment variables are set in Coolify, the issue is likely one of:

1. **Environment variables not being passed to container** (most likely)
2. **spaCy model download failed during build**
3. **App crashes during startup** (database/import error)
4. **Port configuration mismatch**

---

## Immediate Action Steps

### Step 1: Run Diagnostic Script in Coolify Console

1. **Open Coolify Dashboard** → Your Application
2. **Click "Console" or "Shell"** (to get terminal access to container)
3. **Run this command:**
   ```bash
   python healthcheck.py
   ```

This will show you **exactly** what's failing:
- ✓/✗ Environment variables set
- ✓/✗ Modules can import
- ✓/✗ spaCy model available
- ✓/✗ Config loads
- ✓/✗ Database initializes
- ✓/✗ App creates

### Step 2: Check Runtime Logs

1. In Coolify Dashboard → **Logs** → **Runtime Logs**
2. Look for the **last error before crash**

Common errors to look for:
```
ValueError: Missing required configuration: langextract_api_key
ModuleNotFoundError: No module named 'spacy'
OSError: [E050] Can't find model 'en_core_web_sm'
```

### Step 3: Verify Environment Variables in Console

```bash
echo $API_KEY_SECRET
echo $LANGEXTRACT_API_KEY
echo $ENV
```

**Expected output:**
```
test-api-key
AIzaSyAc1rCvcoVjE2S8H95ThGKWjSkyb9xqrro
prod
```

**If empty:** Environment variables aren't being passed to the container.

---

## Likely Fixes (Based on Diagnosis)

### Scenario A: Environment Variables Missing in Container

**Symptoms:**
- `echo $API_KEY_SECRET` returns empty
- healthcheck.py shows: `✗ API_KEY_SECRET`

**Fix:**
1. In Coolify, go to **Environment Variables**
2. Verify variables are in the correct section (not "Build Args")
3. Click **"Restart"** (not just Redeploy)
4. If still doesn't work, try **"Rebuild"**

### Scenario B: spaCy Model Missing

**Symptoms:**
- Runtime logs show: `ModuleNotFoundError: No module named 'spacy'`
- healthcheck.py shows: `✗ spacy`

**Fix:**
1. Check **Build Logs** for spaCy installation errors
2. Look for line: `Successfully installed en_core_web_sm`
3. If missing, rebuild the container

### Scenario C: App Crashes on Import

**Symptoms:**
- Runtime logs show Python traceback
- healthcheck.py shows: `✗ Failed to create app`

**Fix:**
1. Read the full traceback in runtime logs
2. Identify the failing module/line
3. Check if required dependency is installed

### Scenario D: Port Not Listening

**Symptoms:**
- App seems to start but 502 persists
- Runtime logs show no errors

**Fix:**
```bash
# In Coolify console, check if app is listening
netstat -tulpn | grep 8000
# or
ss -tulpn | grep 8000
```

Expected: `0.0.0.0:8000` with `python` or `uvicorn`

---

## What We Changed

### Files Modified:

1. **`healthcheck.py`** (NEW)
   - Comprehensive diagnostic script
   - Tests all startup requirements
   - Run this in Coolify console: `python healthcheck.py`

2. **`main.py`** (FIXED)
   - Removed unused `FastAPI` import
   - Startup event properly registered

3. **`TROUBLESHOOTING_502.md`** (UPDATED)
   - Detailed diagnostic steps
   - Coolify-specific troubleshooting

### To Deploy These Changes:

```powershell
# Commit changes
git add healthcheck.py main.py TROUBLESHOOTING_502.md ACTION_PLAN.md
git commit -m "Add diagnostic healthcheck and fix startup issues"
git push

# Then in Coolify: Click "Redeploy"
```

---

## Testing After Fix

Once you've identified and fixed the issue:

### 1. Test Health Endpoint
```powershell
Invoke-WebRequest -Uri "https://promopack-extractor.powellmatt.com/health" -UseBasicParsing
```

**Expected:** `StatusCode: 200`

### 2. Test API Documentation
```
https://promopack-extractor.powellmatt.com/docs
```

**Expected:** Swagger UI loads

### 3. Test Actual Claim Extraction
```powershell
$headers = @{
    "Authorization" = "Bearer test-api-key"
    "Content-Type" = "application/json"
}

$body = @{
    document_url = "https://example.com/sample.pdf"
    prompt_version = "v4_regulatory"
} | ConvertTo-Json

Invoke-WebRequest `
    -Uri "https://promopack-extractor.powellmatt.com/extract-claims" `
    -Method POST `
    -Headers $headers `
    -Body $body
```

---

## Quick Reference

### Most Important Commands

**In Coolify Console:**
```bash
# Run full diagnostic
python healthcheck.py

# Check environment variables
echo $API_KEY_SECRET
echo $LANGEXTRACT_API_KEY

# Check if app is running
ps aux | grep uvicorn

# Check port
netstat -tulpn | grep 8000

# Test health endpoint internally
curl http://localhost:8000/health
```

**From Your Local Machine:**
```powershell
# Test deployed health endpoint
Invoke-WebRequest -Uri "https://promopack-extractor.powellmatt.com/health" -UseBasicParsing
```

---

## Next Steps

1. ✅ **Run `python healthcheck.py` in Coolify Console** (TOP PRIORITY)
2. ✅ **Check Coolify Runtime Logs** for errors
3. ✅ **Verify environment variables** with `echo $VAR`
4. ✅ **Apply appropriate fix** based on diagnosis
5. ✅ **Test health endpoint** after fix
6. ✅ **Share results** if still stuck

---

## Need More Help?

If the issue persists after following these steps, share:

1. **Output of `python healthcheck.py`** from Coolify console
2. **Last 50 lines of Runtime Logs** from Coolify
3. **Last 50 lines of Build Logs** from Coolify
4. **Output of `echo $API_KEY_SECRET`** (can redact the value)

This will give us the exact information needed to fix the issue.

---

**TL;DR:**
1. Open Coolify console
2. Run `python healthcheck.py`
3. Read the output to see what's failing
4. Apply the appropriate fix from above
5. Redeploy and test
