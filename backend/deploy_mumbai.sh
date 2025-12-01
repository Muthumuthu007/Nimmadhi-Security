#!/bin/bash
# Deploy Django Stock Management System to AWS Mumbai Region

echo "🇮🇳 Deploying to AWS Mumbai (ap-south-1)..."

# Navigate to project directory
cd "/Users/muthuk/Downloads/backend 11/backend 8/backend 4/backend"

# Install EB CLI if not installed
if ! command -v eb &> /dev/null; then
    echo "📦 Installing EB CLI..."
    pip install awsebcli
fi

# Initialize EB application for Mumbai region
echo "🎯 Initializing EB application..."
eb init stock-management-api --region ap-south-1 --platform python-3.11

# Create production environment
echo "🌍 Creating production environment..."
eb create production-mumbai --instance-type t3.small --region ap-south-1

# Set environment variables
echo "⚙️ Setting environment variables..."
eb setenv DJANGO_SECRET_KEY="$(openssl rand -base64 32)"
eb setenv JWT_SECRET="$(openssl rand -base64 32)"
eb setenv DEBUG=False
eb setenv AWS_REGION=ap-south-1
eb setenv RATE_LIMIT_ENABLE=True
eb setenv RATE_LIMIT_PER_MINUTE=60
eb setenv JWT_EXPIRATION_HOURS=6

# Get EB URL and set CORS settings
EB_URL=$(eb status | grep "CNAME" | awk '{print $2}')
eb setenv ALLOWED_HOSTS="$EB_URL,localhost"
eb setenv CSRF_TRUSTED_ORIGINS="https://$EB_URL"

echo "✅ Deployment to Mumbai complete!"
echo "🌐 Your API is live at: https://$EB_URL"
echo ""
echo "📝 Add your AWS credentials:"
echo "eb setenv AWS_ACCESS_KEY_ID=your-key"
echo "eb setenv AWS_SECRET_ACCESS_KEY=your-secret"
echo ""
echo "🧪 Test your API:"
echo "curl https://$EB_URL/api/csrf-token/"