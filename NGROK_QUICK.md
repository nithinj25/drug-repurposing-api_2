# Quick Start: Expose API with ngrok

## 3-Step Quick Setup

### 1️⃣ **Download & Install ngrok**
- Go to: https://ngrok.com/download
- Download for Windows
- Extract to: `C:\ngrok\` (or anywhere convenient)

### 2️⃣ **Create Free Account & Get Token**
- Go to: https://ngrok.com/
- Sign up for free
- Copy your auth token from dashboard
- Run: `ngrok config add-authtoken YOUR_TOKEN`

### 3️⃣ **Expose Your API**

**Terminal 1 - Start FastAPI:**
```powershell
cd c:\Users\Nithin J\OneDrive\Desktop\ey_project\drug-repurposing-assistant
python src/api.py
```

**Terminal 2 - Start ngrok:**
```powershell
ngrok http 8000
```

You'll see:
```
Forwarding    https://abc123def456.ngrok.io -> http://localhost:8000
```

## 4️⃣ **Copy URL & Use in Lovable**

Copy the HTTPS URL (like `https://abc123def456.ngrok.io`)

In Lovable, use this as your API endpoint:
```javascript
const API_URL = 'https://abc123def456.ngrok.io';
```

## ✅ Test It Works

```bash
# Test health endpoint
curl https://abc123def456.ngrok.io/health

# View API docs
https://abc123def456.ngrok.io/docs
```

## ⚠️ Important

- **Keep ngrok running** while using the API
- **New URL each restart** (free tier) - just copy the new URL
- **Public access** - anyone with the URL can reach your API
- **2-hour limit** on free tier - upgrade to $5/month for persistent URL

## Alternative: Install via Chocolatey (If you have it)

```powershell
choco install ngrok
```

Then just run: `ngrok http 8000`

---

**Need help?** Check NGROK_SETUP.md for detailed guide
