#!/usr/bin/env python
"""
Simple script to run the DynamoDB import command
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.core.management import call_command

def main():
    print("DynamoDB Import Utility")
    print("=" * 50)
    
    # Check if AWSDynamoDB directory exists
    data_dir = input("Enter path to DynamoDB export directory (default: AWSDynamoDB): ").strip()
    if not data_dir:
        data_dir = "AWSDynamoDB"
    
    if not os.path.exists(data_dir):
        print(f"Error: Directory '{data_dir}' does not exist")
        return
    
    # Ask for options
    dry_run = input("Run in dry-run mode? (y/N): ").strip().lower() == 'y'
    clear_tables = input("Clear existing data before import? (y/N): ").strip().lower() == 'y'
    
    if clear_tables and not dry_run:
        confirm = input("WARNING: This will delete all existing data! Are you sure? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Import cancelled.")
            return
    
    print(f"\nStarting import from: {data_dir}")
    print(f"Dry run: {dry_run}")
    print(f"Clear tables: {clear_tables}")
    print("-" * 50)
    
    try:
        # Use the auto-detection command
        call_command(
            'import_dynamodb_auto',
            data_dir=data_dir,
            dry_run=dry_run,
            clear_tables=clear_tables,
            verbosity=2
        )
        print("\nImport completed successfully!")
        
    except Exception as e:
        print(f"\nError during import: {e}")
        return

if __name__ == '__main__':
    main()