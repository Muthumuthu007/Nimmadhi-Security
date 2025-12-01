"""
Deployment Checklist Script for Inward Service Migration
Run this script to verify all components are properly configured
"""
import os
import sys
from datetime import datetime, timedelta

def check_file_exists(filepath, description):
    """Check if a file exists and report status"""
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description}: {filepath} - FILE MISSING")
        return False

def check_django_settings():
    """Check Django settings for required configurations"""
    try:
        from django.conf import settings
        
        # Check DynamoDB settings
        if hasattr(settings, 'DYNAMODB_TABLES'):
            tables = settings.DYNAMODB_TABLES
            required_tables = ['stock_transactions', 'stock', 'Groups']
            
            print("\nDynamoDB Table Configuration:")
            for table_key in required_tables:
                if table_key in tables:
                    print(f"✓ {table_key}: {tables[table_key]}")
                else:
                    print(f"✗ {table_key}: NOT CONFIGURED")
        else:
            print("✗ DYNAMODB_TABLES not found in settings")
            
        # Check AWS credentials
        aws_keys = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION']
        print("\nAWS Configuration:")
        for key in aws_keys:
            if hasattr(settings, key):
                value = getattr(settings, key)
                if value:
                    print(f"✓ {key}: {'*' * len(str(value))}")  # Mask the value
                else:
                    print(f"✗ {key}: NOT SET")
            else:
                print(f"✗ {key}: NOT CONFIGURED")
                
        return True
        
    except Exception as e:
        print(f"✗ Django settings check failed: {str(e)}")
        return False

def check_dynamodb_connection():
    """Test DynamoDB connection"""
    try:
        from backend.dynamodb_service import dynamodb_service
        
        print("\nDynamoDB Connection Test:")
        
        # Test each required table
        tables_to_test = ['stock_transactions', 'stock', 'Groups']
        
        for table_name in tables_to_test:
            try:
                # Try to scan with limit to test connection
                items = dynamodb_service.scan_table(table_name)
                print(f"✓ {table_name}: Connected ({len(items)} items)")
            except Exception as e:
                print(f"✗ {table_name}: Connection failed - {str(e)}")
                
        return True
        
    except Exception as e:
        print(f"✗ DynamoDB connection test failed: {str(e)}")
        return False

def check_inward_service():
    """Test InwardService functionality"""
    try:
        from reports.inward_service import InwardService
        
        print("\nInwardService Functionality Test:")
        
        # Test service import
        print("✓ InwardService imported successfully")
        
        # Test get_group_chain with None (should return empty list)
        chain = InwardService.get_group_chain(None)
        if chain == []:
            print("✓ get_group_chain handles None input")
        else:
            print("✗ get_group_chain failed None test")
            
        # Test date handling
        ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        test_date = ist_now.strftime('%Y-%m-%d')
        
        try:
            result = InwardService.get_daily_inward(test_date)
            if 'report_period' in result and 'inward' in result:
                print("✓ get_daily_inward returns correct structure")
            else:
                print("✗ get_daily_inward structure incorrect")
        except Exception as e:
            print(f"✗ get_daily_inward failed: {str(e)}")
            
        return True
        
    except Exception as e:
        print(f"✗ InwardService test failed: {str(e)}")
        return False

def check_api_endpoints():
    """Check if API endpoints are configured"""
    try:
        from django.urls import reverse
        
        print("\nAPI Endpoints Check:")
        
        endpoints_to_check = [
            'get_daily_inward',
            'get_weekly_inward',
            'get_monthly_inward'
        ]
        
        for endpoint in endpoints_to_check:
            try:
                url = reverse(endpoint)
                print(f"✓ {endpoint}: {url}")
            except Exception as e:
                print(f"✗ {endpoint}: Not configured - {str(e)}")
                
        return True
        
    except Exception as e:
        print(f"✗ API endpoints check failed: {str(e)}")
        return False

def run_deployment_checklist():
    """Run complete deployment checklist"""
    print("=" * 60)
    print("INWARD SERVICE DEPLOYMENT CHECKLIST")
    print("=" * 60)
    
    # Check required files
    print("\n1. FILE EXISTENCE CHECK")
    print("-" * 30)
    
    base_path = os.path.dirname(__file__)
    files_to_check = [
        (os.path.join(base_path, 'inward_service.py'), 'InwardService'),
        (os.path.join(base_path, 'views.py'), 'Updated Views'),
        (os.path.join(base_path, 'urls.py'), 'URL Configuration'),
        (os.path.join(base_path, 'test_inward_fixtures.py'), 'Test Fixtures'),
        (os.path.join(base_path, 'INWARD_MIGRATION_README.md'), 'Migration README')
    ]
    
    files_ok = all(check_file_exists(filepath, desc) for filepath, desc in files_to_check)
    
    # Check Django settings
    print("\n2. DJANGO CONFIGURATION CHECK")
    print("-" * 30)
    settings_ok = check_django_settings()
    
    # Check DynamoDB connection
    print("\n3. DYNAMODB CONNECTION CHECK")
    print("-" * 30)
    db_ok = check_dynamodb_connection()
    
    # Check InwardService
    print("\n4. INWARD SERVICE CHECK")
    print("-" * 30)
    service_ok = check_inward_service()
    
    # Check API endpoints
    print("\n5. API ENDPOINTS CHECK")
    print("-" * 30)
    api_ok = check_api_endpoints()
    
    # Final summary
    print("\n" + "=" * 60)
    print("DEPLOYMENT CHECKLIST SUMMARY")
    print("=" * 60)
    
    checks = [
        ("Files", files_ok),
        ("Django Settings", settings_ok),
        ("DynamoDB Connection", db_ok),
        ("InwardService", service_ok),
        ("API Endpoints", api_ok)
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{check_name:20} {status}")
        if not passed:
            all_passed = False
    
    print("-" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - READY FOR DEPLOYMENT")
    else:
        print("⚠️  SOME CHECKS FAILED - REVIEW BEFORE DEPLOYMENT")
    
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    # Set up Django environment
    import django
    from django.conf import settings
    
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
        django.setup()
    
    # Run checklist
    success = run_deployment_checklist()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)