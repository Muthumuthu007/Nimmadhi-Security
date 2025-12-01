# Django Application Hosting Guide

## 🚀 Quick Deployment Options

### 1. **Railway** (Easiest - 5 minutes)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

**Environment Variables in Railway Dashboard:**
```
DJANGO_SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here
DEBUG=False
ALLOWED_HOSTS=your-app.railway.app
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

**Cost:** Free tier available, $5/month paid
**URL:** `https://your-app.railway.app`

### 2. **Heroku** (Popular)
```bash
# Install Heroku CLI
# Create Procfile
echo "web: gunicorn backend.wsgi" > Procfile

# Deploy
heroku create your-app-name
git push heroku main

# Set environment variables
heroku config:set DJANGO_SECRET_KEY="your-secret"
heroku config:set DEBUG=False
```

**Cost:** $7/month minimum
**URL:** `https://your-app.herokuapp.com`

### 3. **DigitalOcean App Platform**
```bash
# Create app.yaml
runtime: python3
services:
- name: web
  source_dir: /
  github:
    repo: your-username/your-repo
    branch: main
  run_command: gunicorn backend.wsgi
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
```

**Cost:** $5/month minimum
**URL:** `https://your-app.ondigitalocean.app`

### 4. **AWS Elastic Beanstalk**
```bash
# Install EB CLI
pip install awsebcli

# Deploy
eb init
eb create production-api
eb setenv DJANGO_SECRET_KEY="your-secret"
eb deploy
```

**Cost:** $10-50/month
**URL:** `https://your-app.region.elasticbeanstalk.com`

## 📋 Pre-Deployment Checklist

### 1. Create Production Requirements
```bash
cd /path/to/your/project
pip freeze > requirements.txt
```

### 2. Create Environment File
```bash
cp .env.security .env
# Edit .env with your production values
```

### 3. Install Production Server
```bash
pip install gunicorn
echo "gunicorn==21.2.0" >> requirements.txt
```

### 4. Create Procfile (for Heroku/Railway)
```bash
echo "web: gunicorn backend.wsgi --bind 0.0.0.0:\$PORT" > Procfile
```

### 5. Update ALLOWED_HOSTS
```python
# In settings.py
ALLOWED_HOSTS = ['your-domain.com', 'localhost', '127.0.0.1']
```

## 🔧 Production Configuration

### Update settings.py for production:
```python
import os

# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # CORS settings
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [
        "https://your-frontend-domain.com",
    ]
```

## 🌐 Domain & SSL Setup

### 1. Custom Domain (Optional)
- Buy domain from Namecheap/GoDaddy
- Point DNS to hosting provider
- Enable SSL certificate

### 2. Environment Variables Required:
```
DJANGO_SECRET_KEY=your-very-secure-secret-key
JWT_SECRET=your-jwt-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-app.railway.app
CSRF_TRUSTED_ORIGINS=https://your-domain.com
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-2
```

## 🚀 Recommended: Railway (Fastest)

1. **Sign up:** https://railway.app
2. **Connect GitHub:** Link your repository
3. **Deploy:** One-click deployment
4. **Set Environment Variables:** In dashboard
5. **Get URL:** Instant HTTPS URL

**Total Time:** 5-10 minutes
**Cost:** Free for small apps

## 📱 Frontend Hosting

If you have a frontend, host it separately:
- **Vercel** (React/Next.js)
- **Netlify** (Static sites)
- **Firebase Hosting** (Any frontend)

## 🔍 Testing Your Deployment

```bash
# Test API endpoints
curl https://your-app.railway.app/api/users/login/ \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'

# Test CSRF token
curl https://your-app.railway.app/api/csrf-token/
```

## 📊 Monitoring (Optional)

- **Sentry** - Error tracking
- **New Relic** - Performance monitoring
- **DataDog** - Infrastructure monitoring

Choose Railway for the quickest deployment - it's perfect for Django apps with minimal configuration needed.