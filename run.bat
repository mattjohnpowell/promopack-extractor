@echo off
REM Quick start script for PromoPack Extractor (Windows)

echo 🚀 PromoPack Claim Extractor - Quick Start
echo ==========================================

REM Check if .env exists
if not exist .env (
    echo 📋 Setting up environment configuration...
    copy .env.example .env
    echo ✅ Created .env file from template
    echo ⚠️  Please edit .env with your actual API keys before running!
    echo    Required: API_KEY_SECRET and LANGEXTRACT_API_KEY
    pause
    exit /b 1
)

REM Check if required environment variables are set (basic check)
findstr /C:"API_KEY_SECRET=" .env >nul
if errorlevel 1 (
    echo ❌ API_KEY_SECRET not found in .env file
    echo    Please set API_KEY_SECRET in .env
    pause
    exit /b 1
)

findstr /C:"LANGEXTRACT_API_KEY=" .env >nul
if errorlevel 1 (
    echo ❌ LANGEXTRACT_API_KEY not found in .env file
    echo    Please set LANGEXTRACT_API_KEY in .env
    pause
    exit /b 1
)

echo 🔨 Building container image...
podman build -t promopack-extractor:latest .

echo 🏃 Starting container...
podman run -d --name promopack-extractor -p 8000:8000 --env-file .env promopack-extractor:latest

echo ⏳ Waiting for service to start...
timeout /t 5 /nobreak >nul

echo 🔍 Testing health endpoint...
curl -f -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Service is healthy!
    echo.
    echo 🌐 API Documentation: http://localhost:8000/docs
    echo 🏥 Health Check:      http://localhost:8000/health
    echo 🛑 To stop:           make podman-stop
    echo.
    echo 🎉 Ready to extract claims from PDFs!
) else (
    echo ❌ Service failed to start properly
    echo    Check logs with: make podman-logs
    pause
    exit /b 1
)

pause