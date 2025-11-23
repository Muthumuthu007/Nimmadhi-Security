#!/usr/bin/env python3
"""
Script to add 'role' attribute to existing users in DynamoDB table
"""
import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.dynamodb_service import dynamodb_service
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_role_to_existing_users():
    """Add role attribute to all existing users in DynamoDB"""
    try:
        # Get all users
        users = dynamodb_service.scan_table('USERS')
        logger.info(f"Found {len(users)} users to update")
        
        updated_count = 0
        for user in users:
            username = user.get('username')
            
            # Skip if role already exists
            if 'role' in user:
                logger.info(f"User {username} already has role: {user['role']}")
                continue
            
            # Set default role based on username
            default_role = 'admin' if username == 'admin' else 'user'
            
            try:
                # Update user with role attribute
                dynamodb_service.update_item(
                    'USERS',
                    {'username': username},
                    'SET #role = :role',
                    {':role': default_role},
                    ExpressionAttributeNames={'#role': 'role'}
                )
                logger.info(f"Added role '{default_role}' to user: {username}")
                updated_count += 1
                
            except ClientError as e:
                logger.error(f"Failed to update user {username}: {e}")
        
        logger.info(f"Successfully updated {updated_count} users with role attribute")
        return True
        
    except Exception as e:
        logger.error(f"Error updating users: {e}")
        return False

if __name__ == "__main__":
    print("Adding 'role' attribute to existing users...")
    success = add_role_to_existing_users()
    if success:
        print("✅ Successfully added role attribute to all users")
    else:
        print("❌ Failed to update users")
        sys.exit(1)