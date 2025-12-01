#!/bin/bash
# AWS Elastic Beanstalk Deployment Script for DynamoDB Django App

echo "🚀 Deploying Django DynamoDB App to AWS Elastic Beanstalk..."

# Step 1: Install AWS CLI and EB CLI
echo "📦 Installing AWS CLI and EB CLI..."
pip install awsebcli

# Step 2: Configure AWS credentials (if not already done)
echo "🔐 Configure AWS credentials..."
echo "Run: aws configure"
echo "Enter your AWS Access Key ID, Secret Access Key, and Region"

# Step 3: Prepare application
echo "📋 Preparing application files..."
pip freeze > requirements.txt

# Add gunicorn if not present
if ! grep -q "gunicorn" requirements.txt; then
    echo "gunicorn==21.2.0" >> requirements.txt
fi

# Step 4: Initialize EB application
echo "🎯 Initializing Elastic Beanstalk application..."
eb init django-casting-api --region us-east-1 --platform python-3.11

# Step 5: Create environment
echo "🌍 Creating production environment..."
eb create production-api --instance-type t3.small

# Step 6: Set environment variables
echo "⚙️ Setting environment variables..."
eb setenv DJANGO_SECRET_KEY="$(openssl rand -base64 32)"
eb setenv JWT_SECRET="$(openssl rand -base64 32)"
eb setenv DEBUG=False
eb setenv AWS_REGION=us-east-2
eb setenv RATE_LIMIT_ENABLE=True
eb setenv RATE_LIMIT_PER_MINUTE=60
eb setenv JWT_EXPIRATION_HOURS=6

# Get the EB environment URL
EB_URL=$(eb status | grep "CNAME" | awk '{print $2}')
eb setenv ALLOWED_HOSTS="$EB_URL,localhost"
eb setenv CSRF_TRUSTED_ORIGINS="https://$EB_URL"

echo "✅ Deployment complete!"
echo "🌐 Your app is available at: https://$EB_URL"
echo ""
echo "📝 Next steps:"
echo "1. Update your AWS credentials in EB environment variables:"
echo "   eb setenv AWS_ACCESS_KEY_ID=your-key"
echo "   eb setenv AWS_SECRET_ACCESS_KEY=your-secret"
echo "2. Test your API endpoints"
echo "3. Set up custom domain (optional)"
echo ""
echo "📊 Monitor your app:"
echo "   eb health    # Check health"
echo "   eb logs      # View logs"
echo "   eb open      # Open in browser"