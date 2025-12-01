#!/usr/bin/env python3
"""
Test script to check if reports are returning all data from selected dates in DB
"""
import os
import sys
import django
from datetime import datetime, timedelta
import json

# Add the project directory to Python path
sys.path.append('/Users/muthuk/Downloads/backend 8/backend 4/backend')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.dynamodb_service import dynamodb_service
from reports.views import get_daily_report, get_weekly_report, get_monthly_report
from django.test import RequestFactory
from django.http import JsonResponse

def test_date_filtering():
    """Test if date filtering is working correctly"""
    print("Testing date filtering in reports...")
    
    # Get actual dates from DB first
    all_transactions = dynamodb_service.scan_table('stock_transactions')
    actual_dates = set()
    for tx in all_transactions:
        date_val = tx.get('date')
        if date_val:
            actual_dates.add(date_val)
    
    if not actual_dates:
        print("No transactions found in database")
        return
    
    # Use the first available date
    test_date = sorted(actual_dates)[0]
    print(f"\n1. Testing with actual date from DB: {test_date}")
    
    try:
        # Get all transactions from DB first
        all_transactions = dynamodb_service.scan_table('stock_transactions')
        print(f"Total transactions in DB: {len(all_transactions)}")
        
        # Show sample transaction dates
        if all_transactions:
            sample_dates = set()
            for tx in all_transactions[:10]:
                date_val = tx.get('date', 'No date')
                sample_dates.add(date_val)
            print(f"Sample dates in DB: {sorted(sample_dates)}")
        
        # Filter transactions manually for the test date
        filtered_transactions = []
        for tx in all_transactions:
            tx_date = tx.get('date', '')
            if tx_date == test_date:
                filtered_transactions.append(tx)
        
        print(f"Transactions for {test_date}: {len(filtered_transactions)}")
        
        # Test daily report
        factory = RequestFactory()
        request_data = {"report_date": test_date}
        request = factory.post('/reports/daily/', 
                             data=json.dumps(request_data),
                             content_type='application/json')
        
        response = get_daily_report(request)
        if isinstance(response, JsonResponse):
            response_data = json.loads(response.content)
            
            # Check if report includes transactions
            report_transactions = response_data.get('transactions', {})
            report_date_transactions = report_transactions.get(test_date, {}).get('operations', [])
            
            print(f"Report returned {len(report_date_transactions)} transactions for {test_date}")
            
            # Compare counts
            if len(report_date_transactions) == len(filtered_transactions):
                print("✅ PASS: Report returns correct number of transactions")
            else:
                print(f"❌ FAIL: Expected {len(filtered_transactions)}, got {len(report_date_transactions)}")
                
                # Show details of missing transactions
                report_tx_ids = {tx.get('transaction_id') for tx in report_date_transactions}
                db_tx_ids = {tx.get('transaction_id') for tx in filtered_transactions}
                
                missing_in_report = db_tx_ids - report_tx_ids
                extra_in_report = report_tx_ids - db_tx_ids
                
                if missing_in_report:
                    print(f"Missing in report: {missing_in_report}")
                if extra_in_report:
                    print(f"Extra in report: {extra_in_report}")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

def test_date_range_filtering():
    """Test date range filtering for weekly/monthly reports"""
    print("\n2. Testing date range filtering...")
    
    # Get actual date range from DB
    all_transactions = dynamodb_service.scan_table('stock_transactions')
    actual_dates = []
    for tx in all_transactions:
        date_val = tx.get('date')
        if date_val:
            actual_dates.append(date_val)
    
    if not actual_dates:
        print("No transactions found for date range test")
        return
    
    actual_dates.sort()
    start_date = actual_dates[0]
    end_date = actual_dates[min(len(actual_dates)-1, 10)]  # Use first 10 dates
    
    try:
        # Get all transactions
        all_transactions = dynamodb_service.scan_table('stock_transactions')
        
        # Filter manually for date range
        filtered_transactions = []
        for tx in all_transactions:
            tx_date = tx.get('date', '')
            if start_date <= tx_date <= end_date:
                filtered_transactions.append(tx)
        
        print(f"DB transactions in range {start_date} to {end_date}: {len(filtered_transactions)}")
        
        # Test weekly report
        factory = RequestFactory()
        request_data = {"start_date": start_date, "end_date": end_date}
        request = factory.post('/reports/weekly/', 
                             data=json.dumps(request_data),
                             content_type='application/json')
        
        response = get_weekly_report(request)
        if isinstance(response, JsonResponse):
            response_data = json.loads(response.content)
            
            # Count transactions in report
            report_transactions = response_data.get('transactions', {})
            total_report_tx = 0
            for date_key, date_data in report_transactions.items():
                total_report_tx += len(date_data.get('operations', []))
            
            print(f"Weekly report returned {total_report_tx} transactions")
            
            if total_report_tx == len(filtered_transactions):
                print("✅ PASS: Weekly report returns correct number of transactions")
            else:
                print(f"❌ FAIL: Expected {len(filtered_transactions)}, got {total_report_tx}")
        
    except Exception as e:
        print(f"Error during date range test: {e}")

def check_dynamodb_filter_expression():
    """Test the DynamoDB filter expression directly"""
    print("\n3. Testing DynamoDB filter expression...")
    
    # Get an actual date from DB
    all_transactions = dynamodb_service.scan_table('stock_transactions')
    actual_dates = [tx.get('date') for tx in all_transactions if tx.get('date')]
    
    if not actual_dates:
        print("No transactions found for filter test")
        return
    
    test_date = actual_dates[0]
    
    try:
        # Test the exact filter used in reports
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date = :report_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':report_date': test_date}
        )
        
        print(f"DynamoDB filter returned {len(transactions)} transactions for {test_date}")
        
        # Also test without filter to compare
        all_transactions = dynamodb_service.scan_table('stock_transactions')
        manual_filter = [tx for tx in all_transactions if tx.get('date') == test_date]
        
        print(f"Manual filter returned {len(manual_filter)} transactions for {test_date}")
        
        if len(transactions) == len(manual_filter):
            print("✅ PASS: DynamoDB filter expression works correctly")
        else:
            print("❌ FAIL: DynamoDB filter expression may have issues")
            
            # Show transaction IDs for debugging
            db_filter_ids = {tx.get('transaction_id') for tx in transactions}
            manual_filter_ids = {tx.get('transaction_id') for tx in manual_filter}
            
            print(f"DB filter IDs: {db_filter_ids}")
            print(f"Manual filter IDs: {manual_filter_ids}")
        
    except Exception as e:
        print(f"Error testing DynamoDB filter: {e}")

def main():
    """Run all tests"""
    print("=" * 60)
    print("TESTING REPORTS DATE FILTERING")
    print("=" * 60)
    
    test_date_filtering()
    test_date_range_filtering() 
    check_dynamodb_filter_expression()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()