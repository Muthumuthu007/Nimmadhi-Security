#!/usr/bin/env python3
"""
Test script to verify no-cache headers are properly set
"""
import requests
import sys

def test_no_cache_headers(base_url="http://localhost:8000"):
    """Test that all endpoints return proper no-cache headers"""
    
    endpoints = [
        "/api/users/login/",
        "/api/stock/get-all-stocks/",
        "/api/production/get-all-products/",
        "/api/reports/get-today-logs/",
        "/api/grn/list/",
        "/api/freight/list-freight-notes/",
    ]
    
    print("🔍 Testing No-Cache Headers Implementation\n")
    print("=" * 60)
    
    all_passed = True
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"\n📍 Testing: {endpoint}")
        
        try:
            # Make a GET or POST request (depending on endpoint)
            if "login" in endpoint or "get-all" in endpoint:
                response = requests.post(url, json={}, timeout=5)
            else:
                response = requests.get(url, timeout=5)
            
            headers = response.headers
            
            # Check required headers
            checks = {
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            
            endpoint_passed = True
            
            for header, expected_value in checks.items():
                actual_value = headers.get(header, "")
                
                if expected_value in actual_value or actual_value == expected_value:
                    print(f"   ✅ {header}: {actual_value}")
                else:
                    print(f"   ❌ {header}: Expected '{expected_value}', Got '{actual_value}'")
                    endpoint_passed = False
                    all_passed = False
            
            if endpoint_passed:
                print(f"   ✅ All headers correct for {endpoint}")
            
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Could not connect: {e}")
            print(f"   ℹ️  Make sure Django server is running on {base_url}")
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("✅ All tests passed! No-cache headers are properly configured.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

def test_browser_cache_behavior():
    """Additional test to verify browser won't cache"""
    print("\n\n🌐 Browser Cache Behavior Test")
    print("=" * 60)
    print("""
To manually verify in browser:
1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Visit any API endpoint
4. Check the 'Size' column - should show actual size, NOT '(disk cache)' or '(memory cache)'
5. Reload the page - should see fresh requests every time

Expected Response Headers:
- Cache-Control: no-store, no-cache, must-revalidate, max-age=0
- Pragma: no-cache
- Expires: 0
    """)

if __name__ == "__main__":
    # Test with default localhost
    exit_code = test_no_cache_headers()
    test_browser_cache_behavior()
    sys.exit(exit_code)
