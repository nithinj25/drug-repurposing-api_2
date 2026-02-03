# Install ngrok and setup for exposing local API
# Run with: powershell -ExecutionPolicy Bypass -File setup-ngrok.ps1

Write-Host "================================" -ForegroundColor Cyan
Write-Host "ngrok Setup for Drug Repurposing API" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if ngrok is installed
Write-Host "Step 1: Checking for ngrok..." -ForegroundColor Yellow
try {
    $ngrokVersion = ngrok --version
    Write-Host "✓ ngrok found: $ngrokVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ ngrok not found. Installing..." -ForegroundColor Red
    Write-Host ""
    Write-Host "MANUAL INSTALLATION REQUIRED:" -ForegroundColor Yellow
    Write-Host "1. Download ngrok from: https://ngrok.com/download" -ForegroundColor Cyan
    Write-Host "2. Extract ngrok.exe to: C:\ngrok\" -ForegroundColor Cyan
    Write-Host "3. Or add ngrok folder to Windows PATH" -ForegroundColor Cyan
    Write-Host "4. Create free account at: https://ngrok.com/" -ForegroundColor Cyan
    Write-Host "5. Run: ngrok config add-authtoken YOUR_TOKEN_HERE" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "Step 2: Checking FastAPI..." -ForegroundColor Yellow

# Check if API is running
$apiHealth = $null
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ FastAPI is running on localhost:8000" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ FastAPI is NOT running on localhost:8000" -ForegroundColor Red
    Write-Host "   Please start API first: python src/api.py" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 3: Starting ngrok..." -ForegroundColor Yellow
Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "ngrok is starting..." -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your API will be exposed at a public URL" -ForegroundColor Cyan
Write-Host "Copy the HTTPS URL and use it in Lovable!" -ForegroundColor Cyan
Write-Host ""

# Start ngrok
ngrok http 8000
