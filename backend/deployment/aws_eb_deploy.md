# AWS Elastic Beanstalk Deployment Guide

## Prerequisites
- AWS Account
- AWS CLI installed
- EB CLI installed

## Step 1: Install AWS CLI & EB CLI
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Install EB CLI
pip install awsebcli

# Configure AWS credentials
aws configure
```

## Step 2: Prepare Application
```bash
cd /Users/muthuk/Downloads/backend\ 8/backend\ 4/backend

# Create requirements.txt
pip freeze > requirements.txt

# Add gunicorn
echo "gunicorn==21.2.0" >> requirements.txt
```

## Step 3: Create .ebextensions
```bash
mkdir .ebextensions
```

Create `.ebextensions/django.config`:
```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: backend.wsgi:application
  aws:elasticbeanstalk:application:environment:
    DJANGO_SETTINGS_MODULE: backend.settings
    PYTHONPATH: /var/app/current:$PYTHONPATH
  aws:elasticbeanstalk:container:python:staticfiles:
    /static/: static/

container_commands:
  01_migrate:
    command: "python manage.py collectstatic --noinput"
    leader_only: true
```

## Step 4: Initialize EB Application
```bash
eb init

# Choose:
# - Region: us-east-1 (or your preferred)
# - Application name: django-casting-api
# - Platform: Python 3.11
# - SSH: Yes (recommended)
```

## Step 5: Create Environment
```bash
eb create production-api

# This will:
# - Create EC2 instance
# - Set up load balancer
# - Deploy your application
```

## Step 6: Set Environment Variables
```bash
eb setenv DJANGO_SECRET_KEY="your-very-secure-secret-key"
eb setenv JWT_SECRET="your-jwt-secret-key"
eb setenv DEBUG=False
eb setenv ALLOWED_HOSTS="production-api.us-east-1.elasticbeanstalk.com"
eb setenv CSRF_TRUSTED_ORIGINS="https://production-api.us-east-1.elasticbeanstalk.com"
eb setenv AWS_ACCESS_KEY_ID="your-aws-access-key"
eb setenv AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
eb setenv AWS_REGION="us-east-2"
eb setenv RATE_LIMIT_ENABLE=True
eb setenv RATE_LIMIT_PER_MINUTE=60
eb setenv JWT_EXPIRATION_HOURS=6
```

## Step 7: Configure HTTPS
```bash
eb config

# In the configuration file, add SSL certificate:
# LoadBalancer:
#   SSLCertificateId: arn:aws:acm:region:account:certificate/certificate-id
```

## Step 8: Deploy Updates
```bash
eb deploy
```

## Step 9: Monitor Application
```bash
eb health
eb logs
eb open  # Opens app in browser
```

**Cost:** ~$15-50/month
**URL:** `https://production-api.region.elasticbeanstalk.com`