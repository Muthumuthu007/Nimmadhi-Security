# AWS Elastic Beanstalk Manual Deployment

## Prerequisites
1. AWS Account with billing enabled
2. AWS CLI installed
3. Your DynamoDB tables already created in AWS

## Step 1: Install Tools
```bash
# Install AWS CLI (if not installed)
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Install EB CLI
pip install awsebcli
```

## Step 2: Configure AWS Credentials
```bash
aws configure
# Enter:
# - AWS Access Key ID: [Your access key]
# - AWS Secret Access Key: [Your secret key]
# - Default region: us-east-1
# - Default output format: json
```

## Step 3: Prepare Application
```bash
cd "/Users/muthuk/Downloads/backend 8/backend 4/backend"

# Create requirements.txt
pip freeze > requirements.txt

# Add gunicorn
echo "gunicorn==21.2.0" >> requirements.txt
```

## Step 4: Initialize EB Application
```bash
eb init

# Choose:
# - Region: us-east-1 (or your preferred)
# - Application name: django-casting-api
# - Platform: Python 3.11
# - CodeCommit: No
# - SSH: Yes
```

## Step 5: Create Environment
```bash
eb create production-api

# This creates:
# - EC2 instance (t3.small)
# - Load balancer
# - Auto scaling group
# - Security groups
```

## Step 6: Set Environment Variables
```bash
# Generate secure keys
DJANGO_SECRET=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)

# Set environment variables
eb setenv DJANGO_SECRET_KEY="$DJANGO_SECRET"
eb setenv JWT_SECRET="$JWT_SECRET"
eb setenv DEBUG=False
eb setenv AWS_REGION="us-east-2"
eb setenv RATE_LIMIT_ENABLE=True
eb setenv RATE_LIMIT_PER_MINUTE=60
eb setenv JWT_EXPIRATION_HOURS=6

# Get your EB URL and set hosts
EB_URL=$(eb status | grep "CNAME" | awk '{print $2}')
eb setenv ALLOWED_HOSTS="$EB_URL,localhost"
eb setenv CSRF_TRUSTED_ORIGINS="https://$EB_URL"

# Set your AWS credentials for DynamoDB access
eb setenv AWS_ACCESS_KEY_ID="your-dynamodb-access-key"
eb setenv AWS_SECRET_ACCESS_KEY="your-dynamodb-secret-key"
```

## Step 7: Deploy Application
```bash
eb deploy
```

## Step 8: Test Your Application
```bash
# Open in browser
eb open

# Test API endpoint
curl https://your-app.us-east-1.elasticbeanstalk.com/api/csrf-token/

# Check health
eb health

# View logs
eb logs
```

## Step 9: Configure HTTPS (Optional)
1. Go to AWS Console > Elastic Beanstalk
2. Select your environment
3. Configuration > Load balancer
4. Add HTTPS listener with SSL certificate

## Step 10: Set up Custom Domain (Optional)
1. Buy domain from Route 53 or external provider
2. Create CNAME record pointing to EB URL
3. Update ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS

## Monitoring & Maintenance
```bash
# View application health
eb health

# View logs
eb logs

# Update application
eb deploy

# Scale application
eb scale 2  # Scale to 2 instances

# Terminate environment (when done)
eb terminate production-api
```

## Cost Estimation
- **t3.small instance**: ~$15/month
- **Load balancer**: ~$18/month
- **Data transfer**: ~$1-5/month
- **Total**: ~$35-40/month

## DynamoDB Integration
Your app is already configured for DynamoDB:
- ✅ No database setup needed
- ✅ Uses existing DynamoDB tables
- ✅ AWS credentials for DynamoDB access
- ✅ Auto-scaling with traffic

Your secure Django DynamoDB application will be live at:
`https://production-api.us-east-1.elasticbeanstalk.com`