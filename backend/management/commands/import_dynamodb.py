import os
import json
import glob
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

class Command(BaseCommand):
    help = 'Import DynamoDB JSON exports into Django models'

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

    def handle(self, *args, **options):
        data_dir = options['data_dir']
        dry_run = options['dry_run']
        
        if not os.path.exists(data_dir):
            self.stdout.write(
                self.style.ERROR(f'Data directory "{data_dir}" does not exist')
            )
            return

        # Table name to Django model mapping
        table_model_mapping = {
            'users': 'users.User',
            'Groups': 'users.Group', 
            'stock': 'stock.Stock',
            'stock_remarks': 'stock.StockRemarks',
            'production': 'production.Product',
            'push_to_production': 'production.PushToProduction',
            'stock_transactions': 'undo.StockTransaction',
            'undo_actions': 'undo.UndoAction',
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

        for table_dir in table_dirs:
            table_path = os.path.join(data_dir, table_dir)
            data_path = os.path.join(table_path, 'data')
            
            if not os.path.exists(data_path):
                self.stdout.write(
                    self.style.WARNING(f'No data directory found in {table_dir}')
                )
                continue

            # Try to determine table name from directory or files
            table_name = self.get_table_name(table_path, data_path)
            
            if not table_name:
                self.stdout.write(
                    self.style.WARNING(f'Could not determine table name for {table_dir}')
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

            # Import data for this table
            self.import_table_data(table_name, data_path, model, dry_run)

    def get_table_name(self, table_path, data_path):
        """Try to determine table name from manifest or first JSON file"""
        # Check for manifest file
        manifest_path = os.path.join(table_path, 'manifest-files.json')
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                    return manifest.get('tableName')
            except:
                pass

        # Try to get from first JSON file
        json_files = glob.glob(os.path.join(data_path, '*.json'))
        if json_files:
            try:
                with open(json_files[0], 'r') as f:
                    data = json.load(f)
                    if 'Items' in data and data['Items']:
                        # This is likely the table name we can infer from context
                        # For now, return None and let the mapping handle it
                        pass
            except:
                pass
        
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
                            return Decimal(str(value))
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
                    return [Decimal(str(n)) for n in value]
                elif key == 'BS':  # Binary Set
                    return list(value)
            
            # If not a DynamoDB type, recursively convert
            return {k: self.convert_dynamodb_json(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [self.convert_dynamodb_json(v) for v in item]
        else:
            return item

    def import_table_data(self, table_name, data_path, model, dry_run):
        """Import all JSON files for a table into the Django model"""
        json_files = glob.glob(os.path.join(data_path, '*.json'))
        
        if not json_files:
            self.stdout.write(
                self.style.WARNING(f'No JSON files found for table {table_name}')
            )
            return

        total_records = 0
        
        self.stdout.write(f'Importing table: {table_name}')
        self.stdout.write(f'Found {len(json_files)} JSON files')

        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                items = data.get('Items', [])
                if not items:
                    continue

                records_in_file = len(items)
                self.stdout.write(f'  Processing {records_in_file} records from {os.path.basename(json_file)}')

                if dry_run:
                    total_records += records_in_file
                    continue

                # Convert and save records
                with transaction.atomic():
                    for item in items:
                        converted_item = self.convert_dynamodb_json(item)
                        
                        # Create model instance
                        try:
                            model_instance = model(**converted_item)
                            model_instance.save()
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Error saving record: {e}')
                            )
                            self.stdout.write(f'Record data: {converted_item}')
                            continue

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
                self.style.SUCCESS(f'Successfully imported {total_records} records for table {table_name}')
            )