#!/usr/bin/env python3
"""
Performance monitoring script to track API response times
"""
import time
import requests
import json
from datetime import datetime

def test_api_performance(base_url):
    """Test API endpoints and measure response times"""
    
    endpoints = [
        {
            'name': 'Daily Report',
            'url': f'{base_url}/reports/daily/',
            'data': {'report_date': '2025-07-15'}
        },
        {
            'name': 'Weekly Report', 
            'url': f'{base_url}/reports/weekly/',
            'data': {'start_date': '2025-07-10', 'end_date': '2025-07-15'}
        },
        {
            'name': 'Stock List',
            'url': f'{base_url}/stock/list/',
            'data': {}
        }
    ]
    
    results = []
    
    for endpoint in endpoints:
        print(f"Testing {endpoint['name']}...")
        
        # Warm up request
        try:
            requests.post(endpoint['url'], json=endpoint['data'], timeout=30)
        except:
            pass
        
        # Measure 3 requests
        times = []
        for i in range(3):
            start_time = time.time()
            try:
                response = requests.post(
                    endpoint['url'], 
                    json=endpoint['data'],
                    timeout=30,
                    headers={'Content-Type': 'application/json'}
                )
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # Convert to ms
                times.append(response_time)
                
                print(f"  Request {i+1}: {response_time:.2f}ms (Status: {response.status_code})")
                
            except Exception as e:
                print(f"  Request {i+1}: ERROR - {e}")
                times.append(None)
        
        # Calculate average
        valid_times = [t for t in times if t is not None]
        if valid_times:
            avg_time = sum(valid_times) / len(valid_times)
            results.append({
                'endpoint': endpoint['name'],
                'avg_response_time': avg_time,
                'times': valid_times
            })
            print(f"  Average: {avg_time:.2f}ms\n")
        else:
            print(f"  All requests failed\n")
    
    return results

def main():
    """Run performance tests"""
    print("=" * 50)
    print("API PERFORMANCE MONITOR")
    print("=" * 50)
    
    # Test localhost
    print("Testing LOCALHOST...")
    localhost_results = test_api_performance('http://localhost:8000')
    
    # Test AWS (update URL when deployed)
    aws_url = input("Enter AWS URL (or press Enter to skip): ").strip()
    aws_results = []
    
    if aws_url:
        print(f"\nTesting AWS ({aws_url})...")
        aws_results = test_api_performance(aws_url)
    
    # Summary
    print("=" * 50)
    print("PERFORMANCE SUMMARY")
    print("=" * 50)
    
    for result in localhost_results:
        print(f"LOCALHOST - {result['endpoint']}: {result['avg_response_time']:.2f}ms")
    
    if aws_results:
        print()
        for result in aws_results:
            print(f"AWS - {result['endpoint']}: {result['avg_response_time']:.2f}ms")
        
        print("\nIMPROVEMENT ANALYSIS:")
        for i, endpoint in enumerate(['Daily Report', 'Weekly Report', 'Stock List']):
            if i < len(localhost_results) and i < len(aws_results):
                local_time = localhost_results[i]['avg_response_time']
                aws_time = aws_results[i]['avg_response_time']
                
                if aws_time > local_time:
                    slowdown = ((aws_time - local_time) / local_time) * 100
                    print(f"{endpoint}: {slowdown:.1f}% slower on AWS")
                else:
                    speedup = ((local_time - aws_time) / local_time) * 100
                    print(f"{endpoint}: {speedup:.1f}% faster on AWS")

if __name__ == "__main__":
    main()