# ngrok Setup Guide - Expose Local API to Internet

## What is ngrok?
ngrok creates a secure public URL that forwards traffic to your local `localhost:8000` API. This allows Lovable and other services to access your local FastAPI.

## Installation

### Windows - Quick Install:

1. **Download ngrok:**
   - Go to https://ngrok.com/download
   - Download for Windows
   - Extract the .zip file

2. **Add ngrok to PATH (Optional but recommended):**
   - Extract ngrok.exe to `C:\ngrok\`
   - Or add extraction folder to Windows PATH

3. **Verify Installation:**
   ```powershell
   ngrok --version
   ```

## Setup & Run

### Step 1: Create Free ngrok Account
1. Go to https://ngrok.com/
2. Sign up for free account
3. Copy your authentication token from dashboard

### Step 2: Authenticate ngrok
```powershell
ngrok config add-authtoken YOUR_AUTH_TOKEN_HERE
```

### Step 3: Expose Your API
Make sure your FastAPI is running on localhost:8000, then run:

```powershell
ngrok http 8000
```

You should see output like:
```
Session Status                online
Account                       your-email@example.com
Version                       3.x.x
Region                        us (United States)
Forwarding                    https://abc123def456.ngrok.io -> http://localhost:8000
Connections                   0/20

Your API is now accessible at: https://abc123def456.ngrok.io
```

### Step 4: Copy Your Public URL
The URL like `https://abc123def456.ngrok.io` is your public API endpoint!

## Use with Lovable

1. Go to Lovable.dev
2. In your frontend code, use the ngrok URL:
   ```javascript
   const API_BASE_URL = 'https://abc123def456.ngrok.io';
   
   // Or make it configurable:
   const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://abc123def456.ngrok.io';
   ```

3. Test endpoints:
   - Health: `https://abc123def456.ngrok.io/health`
   - Docs: `https://abc123def456.ngrok.io/docs`
   - Analyze: `https://abc123def456.ngrok.io/analyze`

## Important Notes

⚠️ **URL Changes:** Each time you restart ngrok, you get a new URL (unless you have a paid plan)

✅ **Keep Running:** Keep ngrok running in a separate terminal while developing

✅ **Public Access:** Your API will be publicly accessible (but only on the ngrok URL)

## Optional: Get Persistent URL (Paid)

ngrok free tier generates new URLs. For a persistent URL:
- Upgrade to ngrok paid plan ($5/month)
- Or use reserved domains (static URLs)

## Alternative: Use Environment Variables

Create a `.env` file:
```
REACT_APP_API_URL=https://YOUR_NGROK_URL.ngrok.io
```

Then in code:
```javascript
const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

## Troubleshooting

**"Command not found: ngrok"**
- Add ngrok to PATH or use full path: `C:\ngrok\ngrok http 8000`

**"Connection refused"**
- Make sure FastAPI is running on localhost:8000

**"Session expired"**
- Free tier sessions last 2 hours, restart ngrok or upgrade

## Quick Startup Script

Create a `start-with-ngrok.ps1`:
```powershell
# Terminal 1: Start API
Write-Host "Starting API..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\Users\Nithin J\OneDrive\Desktop\ey_project\drug-repurposing-assistant'; python src/api.py"

# Terminal 2: Start ngrok
Write-Host "Starting ngrok..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "ngrok http 8000"

Write-Host ""
Write-Host "API will be available at: https://YOUR_NGROK_URL.ngrok.io"
Write-Host "Check ngrok terminal for the exact URL"
```

Run with: `.\start-with-ngrok.ps1`
