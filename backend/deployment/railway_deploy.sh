#!/bin/bash
# Railway Deployment Script

echo "🚀 Deploying Django App to Railway..."

# Step 1: Install Railway CLI
echo "📦 Installing Railway CLI..."
npm install -g @railway/cli

# Step 2: Prepare files
echo "📋 Preparing deployment files..."
pip freeze > requirements.txt
echo "web: gunicorn backend.wsgi --bind 0.0.0.0:\$PORT" > Procfile

# Step 3: Login to Railway
echo "🔐 Login to Railway (browser will open)..."
railway login

# Step 4: Initialize project
echo "🎯 Initializing Railway project..."
railway init

# Step 5: Deploy
echo "🚀 Deploying application..."
railway up

echo "✅ Deployment complete!"
echo "📝 Next steps:"
echo "1. Go to Railway dashboard: https://railway.app/dashboard"
echo "2. Set environment variables:"
echo "   - DJANGO_SECRET_KEY"
echo "   - JWT_SECRET" 
echo "   - DEBUG=False"
echo "   - ALLOWED_HOSTS=your-app.railway.app"
echo "   - AWS_ACCESS_KEY_ID"
echo "   - AWS_SECRET_ACCESS_KEY"
echo "3. Your app will be available at: https://your-app.railway.app"