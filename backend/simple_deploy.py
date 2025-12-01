#!/usr/bin/env python3
"""
Simple deployment script for AWS Mumbai region
"""
import os
import subprocess
import sys

def run_command(cmd, description):
    print(f"🔄 {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False
    print(f"✅ {description} completed")
    return True

def main():
    print("🇮🇳 Deploying Stock Management API to AWS Mumbai...")
    
    # Change to project directory
    os.chdir("/Users/muthuk/Downloads/backend 11/backend 8/backend 4/backend")
    
    # Terminate existing environment
    print("🗑️ Cleaning up existing environment...")
    subprocess.run("eb terminate mumbai-api --force", shell=True, capture_output=True)
    
    # Create new environment with minimal config
    if not run_command(
        "eb create mumbai-stock --instance-type t3.micro --region ap-south-1 --single-instance",
        "Creating new environment"
    ):
        return False
    
    # Get environment URL
    result = subprocess.run("eb status mumbai-stock", shell=True, capture_output=True, text=True)
    if "CNAME:" in result.stdout:
        url = result.stdout.split("CNAME:")[1].strip().split()[0]
        print(f"🌐 Your API is deployed at: https://{url}")
        print(f"🧪 Test with: curl https://{url}/api/csrf-token/")
    
    print("✅ Deployment completed!")
    print("\n📝 Next steps:")
    print("1. Set your AWS credentials:")
    print("   eb setenv AWS_ACCESS_KEY_ID=your-key AWS_SECRET_ACCESS_KEY=your-secret -e mumbai-stock")
    print("2. Test your endpoints")

if __name__ == "__main__":
    main()