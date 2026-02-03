# CORS Issue Explanation & Solution

## What is CORS?

**CORS** = **Cross-Origin Resource Sharing**

It's a security feature in browsers that controls which websites can make requests to your backend API.

### Example:
- Your API runs on: `https://unnominative-harley-nectar-ously.ngrok-free.dev`
- Lovable.dev tries to make a request from: `https://lovable.app` or `https://[preview-id].lovable.app`
- These are **different origins** (different domains) → Browser blocks the request by default
- **CORS headers tell the browser**: "It's OK, I allow Lovable.dev to make requests to my API"

## The "Failed to fetch" Error

When you see "Failed to fetch" in Lovable:

1. **Browser sends a preflight OPTIONS request** to your API
2. **API must respond with CORS headers** like:
   ```
   Access-Control-Allow-Origin: *
   Access-Control-Allow-Methods: GET, POST, OPTIONS
   Access-Control-Allow-Headers: Content-Type
   ```
3. **If API doesn't send these headers** → Browser blocks the actual request
4. **Result**: "Failed to fetch" error

## How We Fixed It

### Updated CORS Configuration in `src/api.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # ✅ Allow ANY origin (including Lovable)
    allow_credentials=False,       # ✅ Must be False when using allow_origins=["*"]
    allow_methods=["*"],           # ✅ Allow all HTTP methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],           # ✅ Accept any request headers
    expose_headers=["*"],          # ✅ Expose all response headers to browser
    max_age=600,                   # ✅ Cache preflight response for 10 minutes
)
```

### Key Changes:

| Setting | Before | After | Why |
|---------|--------|-------|-----|
| `allow_origins` | `["*"]` | `["*"]` | Unchanged - allow all |
| `allow_credentials` | `True` | `False` | Must be False with `["*"]` |
| `expose_headers` | Not set | `["*"]` | Allows browser to read response headers |
| `max_age` | Not set | `600` | Speeds up repeated requests |

## Testing the Fix

### 1. Start Your API:
```powershell
cd "c:\Users\Nithin J\OneDrive\Desktop\ey_project\drug-repurposing-assistant"
python src/api.py
```

### 2. Keep ngrok running in another terminal:
```powershell
ngrok http 8000
```

### 3. Test CORS headers with curl:
```powershell
# Send OPTIONS preflight request
curl -i -X OPTIONS https://unnominative-harley-nectar-ously.ngrok-free.dev/health `
  -H "Origin: https://lovable.app" `
  -H "Access-Control-Request-Method: GET"
```

You should see:
```
HTTP/2 200
access-control-allow-origin: *
access-control-allow-methods: *
access-control-allow-headers: *
access-control-expose-headers: *
```

### 4. Test actual request:
```powershell
curl -X POST "https://unnominative-harley-nectar-ously.ngrok-free.dev/analyze" `
  -H "Content-Type: application/json" `
  -H "Origin: https://lovable.app" `
  -d '{"drug_name":"metformin","indication":"cardiovascular disease"}'
```

## Troubleshooting

### Still getting "Failed to fetch"?

1. **Restart the API**:
   - Stop `python src/api.py`
   - Start it again
   - Ensure ngrok is still running

2. **Check ngrok is working**:
   ```powershell
   # Visit in browser
   https://unnominative-harley-nectar-ously.ngrok-free.dev/health
   # Should show: {"status":"healthy","message":"..."}
   ```

3. **Verify Lovable settings**:
   - In Lovable, update API URL to: `https://unnominative-harley-nectar-ously.ngrok-free.dev`
   - No `/health` or `/analyze` in the base URL
   - Make sure it uses `https://` not `http://`

4. **Browser console checks** (in Lovable):
   - Press F12 → Console tab
   - Look for exact error message
   - Check Network tab → see what request was sent

### "endpoint is offline" on ngrok page?

- FastAPI is not running or ngrok forwarding is broken
- Start `python src/api.py` in a terminal
- Verify output shows: `Uvicorn running on http://0.0.0.0:8000`

## Important Notes

1. **`allow_origins=["*"]` with `allow_credentials=True` is a mistake**
   - These two conflict with each other
   - We set `allow_credentials=False` to fix this
   - This is safe for public APIs (like yours)

2. **ngrok URL changes every 2 hours** (free plan)
   - After 2 hours, you'll get a new URL
   - Must update Lovable with the new URL
   - To keep same URL: Upgrade ngrok Pro

3. **In production**, you might want to specify exact domains:
   ```python
   allow_origins=[
       "https://yourdomain.com",
       "https://app.yourdomain.com",
       "https://*.lovable.app"
   ]
   ```

## Summary

✅ **We fixed CORS by:**
- Allowing all origins
- Allowing all HTTP methods
- Allowing all headers
- Adding proper max_age for caching
- Setting credentials to False (correct for public API)

✅ **Result:**
- Lovable can now make requests to your API via ngrok tunnel
- No more "Failed to fetch" error
- Browser preflight requests properly handled

✅ **Next steps:**
1. Start the API
2. Keep ngrok running
3. Configure Lovable with your ngrok URL
4. Test drug analysis through Lovable UI
