"""
Test script for Freight Inward Note API
"""
import requests
import json
from datetime import datetime

# Base URL for the API
BASE_URL = "http://localhost:8000/api"

def test_freight_api():
    """Test all freight API endpoints"""
    
    print("🚛 Testing Freight Inward Note API")
    print("=" * 50)
    
    # Test data
    freight_data = {
        "operation": "CreateFreightNote",
        "transport_vendor": "ABC Transport Co.",
        "total_amount": 15000.00,
        "date": "2024-01-15",
        "created_by": "test_user",
        "allocations": [
            {
                "supplier_name": "Supplier A",
                "amount": 8000.00
            },
            {
                "supplier_name": "Supplier B", 
                "amount": 4000.00
            },
            {
                "supplier_name": "Supplier C",
                "amount": 3000.00
            }
        ]
    }
    
    # Test 1: Create Freight Note
    print("1. Testing Create Freight Note...")
    try:
        response = requests.post(f"{BASE_URL}/lambda/", json=freight_data)
        if response.status_code == 200:
            result = response.json()
            freight_id = result['freight_note']['freight_id']
            print(f"   ✓ Created freight note with ID: {freight_id}")
            print(f"   ✓ Transport Vendor: {result['freight_note']['transport_vendor']}")
            print(f"   ✓ Total Amount: {result['freight_note']['total_amount']}")
            print(f"   ✓ Allocations: {len(result['freight_note']['allocations'])}")
        else:
            print(f"   ✗ Error: {response.text}")
            return
    except Exception as e:
        print(f"   ✗ Exception: {e}")
        return
    
    # Test 2: Get Freight Note
    print("\n2. Testing Get Freight Note...")
    try:
        get_data = {
            "operation": "GetFreightNote",
            "freight_id": freight_id
        }
        response = requests.post(f"{BASE_URL}/lambda/", json=get_data)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Retrieved freight note: {result['freight_note']['transport_vendor']}")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    # Test 3: List Freight Notes
    print("\n3. Testing List Freight Notes...")
    try:
        list_data = {"operation": "ListFreightNotes"}
        response = requests.post(f"{BASE_URL}/lambda/", json=list_data)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Found {len(result['freight_notes'])} freight notes")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    # Test 4: Update Freight Note
    print("\n4. Testing Update Freight Note...")
    try:
        update_data = {
            "operation": "UpdateFreightNote",
            "freight_id": freight_id,
            "transport_vendor": "XYZ Transport Ltd.",
            "total_amount": 16000.00,
            "allocations": [
                {
                    "supplier_name": "Supplier A",
                    "amount": 9000.00
                },
                {
                    "supplier_name": "Supplier B",
                    "amount": 7000.00
                }
            ]
        }
        response = requests.post(f"{BASE_URL}/lambda/", json=update_data)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Updated freight note: {result['freight_note']['transport_vendor']}")
            print(f"   ✓ New total amount: {result['freight_note']['total_amount']}")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    # Test 5: Validation Error (mismatched amounts)
    print("\n5. Testing Validation (should fail)...")
    try:
        invalid_data = {
            "operation": "CreateFreightNote",
            "transport_vendor": "Test Transport",
            "total_amount": 10000.00,
            "date": "2024-01-16",
            "created_by": "test_user",
            "allocations": [
                {
                    "supplier_name": "Supplier X",
                    "amount": 5000.00
                },
                {
                    "supplier_name": "Supplier Y",
                    "amount": 4000.00  # Total: 9000, but freight total is 10000
                }
            ]
        }
        response = requests.post(f"{BASE_URL}/lambda/", json=invalid_data)
        if response.status_code == 400:
            print("   ✓ Validation correctly rejected mismatched amounts")
        else:
            print(f"   ✗ Validation failed: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    # Test 6: Delete Freight Note
    print("\n6. Testing Delete Freight Note...")
    try:
        delete_data = {
            "operation": "DeleteFreightNote",
            "freight_id": freight_id
        }
        response = requests.post(f"{BASE_URL}/lambda/", json=delete_data)
        if response.status_code == 200:
            print("   ✓ Freight note deleted successfully")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Freight API testing completed!")


def test_direct_endpoints():
    """Test direct API endpoints (alternative to lambda handler)"""
    
    print("\n🔗 Testing Direct Freight Endpoints")
    print("=" * 50)
    
    # Test data
    freight_data = {
        "transport_vendor": "Direct Test Transport",
        "total_amount": 12000.00,
        "date": "2024-01-17",
        "created_by": "direct_test_user",
        "allocations": [
            {
                "supplier_name": "Direct Supplier A",
                "amount": 7000.00
            },
            {
                "supplier_name": "Direct Supplier B",
                "amount": 5000.00
            }
        ]
    }
    
    # Test create via direct endpoint
    print("1. Testing direct create endpoint...")
    try:
        response = requests.post(f"{BASE_URL}/freight/create/", json=freight_data)
        if response.status_code == 200:
            result = response.json()
            freight_id = result['freight_note']['freight_id']
            print(f"   ✓ Created via direct endpoint: {freight_id}")
        else:
            print(f"   ✗ Error: {response.text}")
            return
    except Exception as e:
        print(f"   ✗ Exception: {e}")
        return
    
    # Test list via direct endpoint
    print("\n2. Testing direct list endpoint...")
    try:
        response = requests.post(f"{BASE_URL}/freight/list/", json={})
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Listed {len(result['freight_notes'])} freight notes via direct endpoint")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Direct endpoint testing completed!")


if __name__ == "__main__":
    print("Make sure Django server is running on localhost:8000")
    print("Run: python manage.py runserver")
    print("\nPress Enter to continue with testing...")
    input()
    
    test_freight_api()
    test_direct_endpoints()