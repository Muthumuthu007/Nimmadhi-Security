import os
import json
import glob
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

class Command(BaseCommand):
    help = 'Auto-detect and import DynamoDB JSON exports into Django models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='AWSDynamoDB',
            help='Directory containing DynamoDB export folders (default: AWSDynamoDB)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
        parser.add_argument(
            '--clear-tables',
            action='store_true',
            help='Clear existing data in tables before importing'
        )

    def handle(self, *args, **options):
        data_dir = options['data_dir']
        dry_run = options['dry_run']
        clear_tables = options['clear_tables']
        
        if not os.path.exists(data_dir):
            self.stdout.write(
                self.style.ERROR(f'Data directory "{data_dir}" does not exist')
            )
            return

        # Enhanced table name to Django model mapping for all 11 tables
        table_model_mapping = {
            'users': 'users.User',
            'Groups': 'users.Group', 
            'stock': 'stock.Stock',
            'stock_remarks': 'stock.StockRemarks',
            'production': 'production.Product',
            'push_to_production': 'production.PushToProduction',
            'stock_transactions': 'undo.StockTransaction',
            'undo_actions': 'undo.UndoAction',
            'transactions': 'undo.StockTransaction',  # Alternative transactions table
            'YourStockTableName': 'stock.Stock',     # Alternative stock table
            'YourTransactionsTableName': 'undo.StockTransaction',  # Alternative transactions
        }

        # Get all table export directories
        table_dirs = [d for d in os.listdir(data_dir) 
                     if os.path.isdir(os.path.join(data_dir, d))]
        
        if not table_dirs:
            self.stdout.write(
                self.style.WARNING(f'No table directories found in "{data_dir}"')
            )
            return

        self.stdout.write(f'Found {len(table_dirs)} table export directories')

        # First pass: detect table names
        detected_tables = {}
        for table_dir in table_dirs:
            table_path = os.path.join(data_dir, table_dir)
            table_name = self.detect_table_name(table_path)
            if table_name:
                detected_tables[table_dir] = table_name
                self.stdout.write(f'Detected table: {table_name} in directory {table_dir}')

        if not detected_tables:
            self.stdout.write(self.style.ERROR('No tables could be detected'))
            return

        # Second pass: import data
        for table_dir, table_name in detected_tables.items():
            table_path = os.path.join(data_dir, table_dir)
            data_path = os.path.join(table_path, 'data')
            
            if not os.path.exists(data_path):
                self.stdout.write(
                    self.style.WARNING(f'No data directory found in {table_dir}')
                )
                continue

            # Get Django model
            model_path = table_model_mapping.get(table_name)
            if not model_path:
                self.stdout.write(
                    self.style.WARNING(f'No Django model mapping found for table "{table_name}"')
                )
                continue

            try:
                app_label, model_name = model_path.split('.')
                model = apps.get_model(app_label, model_name)
            except (ValueError, LookupError) as e:
                self.stdout.write(
                    self.style.ERROR(f'Could not load model {model_path}: {e}')
                )
                continue

            # Clear existing data if requested
            if clear_tables and not dry_run:
                count = model.objects.count()
                model.objects.all().delete()
                self.stdout.write(f'Cleared {count} existing records from {table_name}')

            # Import data for this table
            self.import_table_data(table_name, data_path, model, dry_run)

    def detect_table_name(self, table_path):
        """Auto-detect table name from manifest or summary files"""
        # Method 1: Check manifest-summary.json (most reliable)
        summary_path = os.path.join(table_path, 'manifest-summary.json')
        if os.path.exists(summary_path):
            try:
                with open(summary_path, 'r') as f:
                    summary = json.load(f)
                    # Extract table name from ARN: arn:aws:dynamodb:region:account:table/TableName/export/...
                    table_arn = summary.get('tableArn')
                    if table_arn:
                        # Parse ARN to get table name
                        arn_parts = table_arn.split(':')
                        if len(arn_parts) >= 6:
                            resource_part = arn_parts[5]  # table/TableName
                            if resource_part.startswith('table/'):
                                return resource_part.split('/')[1]
                    
                    # Fallback to direct tableName field
                    table_name = summary.get('tableName')
                    if table_name:
                        return table_name
            except Exception as e:
                self.stdout.write(f'Error reading summary: {e}')

        # Method 2: Check manifest-files.json
        manifest_path = os.path.join(table_path, 'manifest-files.json')
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                    table_name = manifest.get('tableName')
                    if table_name:
                        return table_name
            except Exception as e:
                self.stdout.write(f'Error reading manifest: {e}')

        return None

    def convert_dynamodb_json(self, item):
        """Convert DynamoDB JSON format to Python values"""
        if isinstance(item, dict):
            if len(item) == 1:
                key, value = next(iter(item.items()))
                if key == 'S':  # String
                    return str(value)
                elif key == 'N':  # Number
                    try:
                        if '.' in str(value):
                            return float(value)
                        else:
                            return int(value)
                    except:
                        return Decimal(str(value))
                elif key == 'B':  # Binary
                    return value
                elif key == 'BOOL':  # Boolean
                    return bool(value)
                elif key == 'NULL':  # Null
                    return None
                elif key == 'L':  # List
                    return [self.convert_dynamodb_json(v) for v in value]
                elif key == 'M':  # Map
                    return {k: self.convert_dynamodb_json(v) for k, v in value.items()}
                elif key == 'SS':  # String Set
                    return list(value)
                elif key == 'NS':  # Number Set
                    return [float(n) if '.' in str(n) else int(n) for n in value]
                elif key == 'BS':  # Binary Set
                    return list(value)
            
            # If not a DynamoDB type, recursively convert
            return {k: self.convert_dynamodb_json(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [self.convert_dynamodb_json(v) for v in item]
        else:
            return item

    def clean_field_data(self, model, field_name, value):
        """Clean and validate field data for Django model"""
        try:
            field = model._meta.get_field(field_name)
            
            # Handle different field types
            if hasattr(field, 'max_length') and field.max_length:
                if isinstance(value, str) and len(value) > field.max_length:
                    value = value[:field.max_length]
            
            # Convert Decimal to float for FloatField
            if field.__class__.__name__ == 'FloatField' and isinstance(value, Decimal):
                value = float(value)
            
            # Handle JSON fields
            if field.__class__.__name__ == 'JSONField':
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except:
                        pass
            
            return value
        except:
            return value

    def import_table_data(self, table_name, data_path, model, dry_run):
        """Import all JSON files for a table into the Django model"""
        json_files = glob.glob(os.path.join(data_path, '*.json'))
        
        if not json_files:
            self.stdout.write(
                self.style.WARNING(f'No JSON files found for table {table_name}')
            )
            return

        total_records = 0
        successful_records = 0
        failed_records = 0
        
        self.stdout.write(f'\nImporting table: {table_name}')
        self.stdout.write(f'Found {len(json_files)} JSON files')

        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        continue
                    
                    # Handle DynamoDB export format - each line is a separate JSON object
                    items = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line:
                            try:
                                line_data = json.loads(line)
                                if 'Item' in line_data:
                                    items.append(line_data['Item'])
                                elif isinstance(line_data, dict):
                                    items.append(line_data)
                            except json.JSONDecodeError:
                                continue
                    
                    if not items:
                        continue

                records_in_file = len(items)
                self.stdout.write(f'  Processing {records_in_file} records from {os.path.basename(json_file)}')

                if dry_run:
                    total_records += records_in_file
                    continue

                # Convert and save records
                for item in items:
                    try:
                        converted_item = self.convert_dynamodb_json(item)
                        
                        # Clean field data
                        cleaned_item = {}
                        for field_name, value in converted_item.items():
                            cleaned_item[field_name] = self.clean_field_data(model, field_name, value)
                        
                        # Create model instance
                        model_instance = model(**cleaned_item)
                        model_instance.save()
                        successful_records += 1
                        
                    except Exception as e:
                        failed_records += 1
                        self.stdout.write(
                            self.style.ERROR(f'    Error saving record: {e}')
                        )
                        # Show first few characters of problematic data
                        item_preview = str(item)[:200] + '...' if len(str(item)) > 200 else str(item)
                        self.stdout.write(f'    Record preview: {item_preview}')

                total_records += records_in_file

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing file {json_file}: {e}')
                )
                continue

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would import {total_records} records for table {table_name}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Completed import for table {table_name}: '
                    f'{successful_records} successful, {failed_records} failed, '
                    f'{total_records} total records processed'
                )
            )