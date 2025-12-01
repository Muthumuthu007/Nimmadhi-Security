#!/usr/bin/env python3
"""
Comprehensive test to identify potential issues with date filtering in reports
"""
import os
import sys
import django
from datetime import datetime, timedelta
import json
from collections import defaultdict

# Add the project directory to Python path
sys.path.append('/Users/muthuk/Downloads/backend 8/backend 4/backend')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.dynamodb_service import dynamodb_service

def analyze_date_distribution():
    """Analyze the distribution of dates in the database"""
    print("Analyzing date distribution in database...")
    
    try:
        all_transactions = dynamodb_service.scan_table('stock_transactions')
        print(f"Total transactions: {len(all_transactions)}")
        
        # Count transactions by date
        date_counts = defaultdict(int)
        date_formats = set()
        invalid_dates = []
        
        for tx in all_transactions:
            date_val = tx.get('date')
            if date_val:
                date_counts[date_val] += 1
                date_formats.add(type(date_val).__name__)
                
                # Check if date format is valid
                try:
                    datetime.strptime(date_val, '%Y-%m-%d')
                except ValueError:
                    invalid_dates.append(date_val)
            else:
                date_counts['NO_DATE'] += 1
        
        print(f"\\nDate formats found: {date_formats}")
        print(f"Invalid date formats: {len(invalid_dates)}")
        if invalid_dates:
            print(f"Sample invalid dates: {invalid_dates[:5]}")
        
        # Show top 10 dates by transaction count
        sorted_dates = sorted(date_counts.items(), key=lambda x: x[1], reverse=True)
        print(f"\\nTop 10 dates by transaction count:")
        for date_val, count in sorted_dates[:10]:
            print(f"  {date_val}: {count} transactions")
        
        return sorted_dates
        
    except Exception as e:
        print(f"Error analyzing dates: {e}")
        return []

def test_edge_cases():
    """Test edge cases that might cause issues"""
    print("\\nTesting edge cases...")
    
    try:
        # Test with empty date
        print("1. Testing empty date filter...")
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date = :report_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':report_date': ''}
        )
        print(f"   Empty date returned: {len(transactions)} transactions")
        
        # Test with null/None date
        print("2. Testing null date filter...")
        try:
            transactions = dynamodb_service.scan_table(
                'stock_transactions',
                FilterExpression='attribute_not_exists(#date)',
                ExpressionAttributeNames={'#date': 'date'}
            )
            print(f"   Null date returned: {len(transactions)} transactions")
        except Exception as e:
            print(f"   Null date test failed: {e}")
        
        # Test with future date
        print("3. Testing future date...")
        future_date = "2030-12-31"
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date = :report_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':report_date': future_date}
        )
        print(f"   Future date {future_date} returned: {len(transactions)} transactions")
        
        # Test with invalid date format
        print("4. Testing invalid date format...")
        invalid_date = "2025/07/15"  # Wrong format
        transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date = :report_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':report_date': invalid_date}
        )
        print(f"   Invalid date {invalid_date} returned: {len(transactions)} transactions")
        
    except Exception as e:
        print(f"Error in edge case testing: {e}")

def test_date_range_boundaries():
    """Test date range boundary conditions"""
    print("\\nTesting date range boundaries...")
    
    try:
        # Get actual dates from DB
        all_transactions = dynamodb_service.scan_table('stock_transactions')
        actual_dates = sorted([tx.get('date') for tx in all_transactions if tx.get('date')])
        
        if len(actual_dates) < 2:
            print("Not enough dates for boundary testing")
            return
        
        # Test inclusive boundaries
        start_date = actual_dates[0]
        end_date = actual_dates[1]
        
        print(f"Testing range: {start_date} to {end_date}")
        
        # Manual count
        manual_count = 0
        for tx in all_transactions:
            tx_date = tx.get('date', '')
            if start_date <= tx_date <= end_date:
                manual_count += 1
        
        # DynamoDB filter count
        db_transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date BETWEEN :start_date AND :end_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={
                ':start_date': start_date,
                ':end_date': end_date
            }
        )
        
        print(f"Manual count: {manual_count}")
        print(f"DynamoDB count: {len(db_transactions)}")
        
        if manual_count == len(db_transactions):
            print("✅ PASS: Date range filtering works correctly")
        else:
            print("❌ FAIL: Date range filtering has issues")
        
    except Exception as e:
        print(f"Error in boundary testing: {e}")

def check_transaction_completeness():
    """Check if all transactions for a date are being returned"""
    print("\\nChecking transaction completeness...")
    
    try:
        # Get a date with many transactions
        all_transactions = dynamodb_service.scan_table('stock_transactions')
        date_counts = defaultdict(list)
        
        for tx in all_transactions:
            date_val = tx.get('date')
            if date_val:
                date_counts[date_val].append(tx)
        
        # Find date with most transactions
        if not date_counts:
            print("No dated transactions found")
            return
        
        busiest_date = max(date_counts.keys(), key=lambda d: len(date_counts[d]))
        expected_transactions = date_counts[busiest_date]
        
        print(f"Testing completeness for busiest date: {busiest_date}")
        print(f"Expected transactions: {len(expected_transactions)}")
        
        # Get transactions using filter
        filtered_transactions = dynamodb_service.scan_table(
            'stock_transactions',
            FilterExpression='#date = :report_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={':report_date': busiest_date}
        )
        
        print(f"Filtered transactions: {len(filtered_transactions)}")
        
        # Check if all transaction IDs match
        expected_ids = {tx.get('transaction_id') for tx in expected_transactions}
        filtered_ids = {tx.get('transaction_id') for tx in filtered_transactions}
        
        missing_ids = expected_ids - filtered_ids
        extra_ids = filtered_ids - expected_ids
        
        if not missing_ids and not extra_ids:
            print("✅ PASS: All transactions returned correctly")
        else:
            print("❌ FAIL: Transaction mismatch detected")
            if missing_ids:
                print(f"Missing transaction IDs: {list(missing_ids)[:5]}")
            if extra_ids:
                print(f"Extra transaction IDs: {list(extra_ids)[:5]}")
        
    except Exception as e:
        print(f"Error checking completeness: {e}")

def main():
    """Run comprehensive date filtering tests"""
    print("=" * 70)
    print("COMPREHENSIVE DATE FILTERING ANALYSIS")
    print("=" * 70)
    
    date_distribution = analyze_date_distribution()
    test_edge_cases()
    test_date_range_boundaries()
    check_transaction_completeness()
    
    print("\\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    
    # Summary
    if date_distribution:
        total_transactions = sum(count for _, count in date_distribution)
        unique_dates = len([d for d, c in date_distribution if d != 'NO_DATE'])
        print(f"\\nSUMMARY:")
        print(f"- Total transactions: {total_transactions}")
        print(f"- Unique dates: {unique_dates}")
        print(f"- Date range: {date_distribution[-1][0]} to {date_distribution[0][0] if date_distribution[0][0] != 'NO_DATE' else date_distribution[1][0]}")

if __name__ == "__main__":
    main()