#!/bin/bash
# Quick start script for PromoPack Extractor

set -e

echo "🚀 PromoPack Claim Extractor - Quick Start"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "📋 Setting up environment configuration..."
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo "⚠️  Please edit .env with your actual API keys before running!"
    echo "   Required: API_KEY_SECRET and LANGEXTRACT_API_KEY"
    exit 1
fi

# Check if required environment variables are set
if ! grep -q "API_KEY_SECRET=.*[^[:space:]]" .env || ! grep -q "LANGEXTRACT_API_KEY=.*[^[:space:]]" .env; then
    echo "❌ API keys not configured in .env file"
    echo "   Please set API_KEY_SECRET and LANGEXTRACT_API_KEY in .env"
    exit 1
fi

echo "🔨 Building container image..."
podman build -t promopack-extractor:latest .

echo "🏃 Starting container..."
podman run -d --name promopack-extractor \
    -p 8000:8000 \
    --env-file .env \
    promopack-extractor:latest

echo "⏳ Waiting for service to start..."
sleep 5

echo "🔍 Testing health endpoint..."
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo "✅ Service is healthy!"
    echo ""
    echo "🌐 API Documentation: http://localhost:8000/docs"
    echo "🏥 Health Check:      http://localhost:8000/health"
    echo "🛑 To stop:           make podman-stop"
    echo ""
    echo "🎉 Ready to extract claims from PDFs!"
else
    echo "❌ Service failed to start properly"
    echo "   Check logs with: make podman-logs"
    exit 1
fi