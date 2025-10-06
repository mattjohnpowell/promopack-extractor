# Docker Build Fix - spaCy Model Download Issue

## Problem

The Docker build was failing with a 404 error when trying to download the spaCy language model:

```
ERROR: HTTP error 404 while getting https://github.com/explosion/spacy-models/releases/download/-en_core_web_sm/-en_core_web_sm.tar.gz
```

**Root Cause:** The `python -m spacy download en_core_web_sm` command was generating a malformed URL in the Docker build context.

---

## Solution

Changed from using the spaCy CLI download command to direct pip installation of the model wheel file.

### Before (Broken)
```dockerfile
RUN python -m spacy download en_core_web_sm
```

### After (Fixed)
```dockerfile
RUN pip install --no-cache-dir --user https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
```

---

## Files Updated

1. **Dockerfile** - Changed spaCy model installation method
2. **Makefile** - Updated `install` and `install-dev` targets
3. **README.md** - Updated installation instructions

---

## Why This Works

- **Direct wheel URL:** Bypasses the spaCy model download resolution logic
- **Version pinned:** Uses `en_core_web_sm-3.7.1` compatible with `spacy==3.7.2`
- **Docker compatible:** Works reliably in containerized builds
- **Same result:** Installs the exact same model, just via a different method

---

## Testing

Rebuild the Docker/Podman image:

```bash
# Podman
podman build -t promopack-extractor:latest .

# Docker
docker build -t promopack-extractor:latest .
```

Expected output:
```
✅ Successfully installed en_core_web_sm-3.7.1
```

---

## Local Development

For local development, you can still use either method:

**Option 1: Direct pip install (recommended)**
```bash
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
```

**Option 2: spaCy CLI (should work locally)**
```bash
python -m spacy download en_core_web_sm
```

Both install the same model - the first method is just more reliable in Docker builds.

---

## Verification

After installation, verify the model is available:

```python
import spacy

# Load the model
nlp = spacy.load("en_core_web_sm")

# Test it
doc = nlp("This is a test sentence.")
print(f"✅ spaCy model loaded successfully! Tokens: {len(doc)}")
```

---

## Related Issues

This is a known issue with spaCy model downloads in Docker containers:
- https://github.com/explosion/spaCy/issues/4577
- https://github.com/explosion/spaCy/discussions/9018

The pip install method is the recommended workaround for production Docker builds.
