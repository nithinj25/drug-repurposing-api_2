# Drug Repurposing Assistant - Startup Script
# Run both API and Frontend

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Drug Repurposing Assistant" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if Python is installed
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found! Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Step 2: Check if Node.js is installed
Write-Host "Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js not found! Please install Node.js" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting services..." -ForegroundColor Cyan
Write-Host ""

# Step 3: Start API
Write-Host "1. Starting API on http://localhost:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python src/api.py"

# Wait for API to start
Write-Host "   Waiting 5 seconds for API to start..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Step 4: Start Frontend
Write-Host "2. Starting React Frontend on http://localhost:3000..." -ForegroundColor Yellow
cd "$PSScriptRoot\ui-react"

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "   Installing dependencies..." -ForegroundColor Gray
    npm install
}

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "✓ Services Starting!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "API:      http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Green
Write-Host ""

npm start
