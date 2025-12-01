"""
Freight Inward Note Models for DynamoDB
"""
import boto3
from decimal import Decimal
from datetime import datetime
from django.conf import settings
import uuid


class FreightInwardService:
    """Service class for Freight Inward operations using DynamoDB"""
    
    def __init__(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.freight_table = self.dynamodb.Table('freight_inward')
        self.allocation_table = self.dynamodb.Table('freight_allocations')
    
    def create_freight_note(self, transport_vendor, total_amount, date, created_by, allocations):
        """Create a new freight inward note with allocations"""
        
        # Validate allocations sum equals total amount
        allocation_sum = sum(Decimal(str(allocation['amount'])) for allocation in allocations)
        if allocation_sum != Decimal(str(total_amount)):
            raise ValueError(f"Total amount ({total_amount}) does not match sum of allocations ({allocation_sum})")
        
        freight_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Create freight header
        freight_item = {
            'freight_id': freight_id,
            'transport_vendor': transport_vendor,
            'total_amount': Decimal(str(total_amount)),
            'date': date,
            'created_by': created_by,
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        try:
            # Save freight header
            self.freight_table.put_item(Item=freight_item)
            
            # Save allocations
            for allocation in allocations:
                allocation_item = {
                    'allocation_id': str(uuid.uuid4()),
                    'freight_id': freight_id,
                    'supplier_name': allocation['supplier_name'],
                    'amount': Decimal(str(allocation['amount'])),
                    'created_at': timestamp
                }
                self.allocation_table.put_item(Item=allocation_item)
            
            return self.get_freight_note(freight_id)
            
        except Exception as e:
            # Cleanup on error
            try:
                self.freight_table.delete_item(Key={'freight_id': freight_id})
            except:
                pass
            raise e
    
    def get_freight_note(self, freight_id):
        """Get freight note with allocations"""
        try:
            # Get freight header
            response = self.freight_table.get_item(Key={'freight_id': freight_id})
            if 'Item' not in response:
                return None
            
            freight = response['Item']
            
            # Get allocations
            allocations_response = self.allocation_table.scan(
                FilterExpression='freight_id = :freight_id',
                ExpressionAttributeValues={':freight_id': freight_id}
            )
            
            freight['allocations'] = allocations_response.get('Items', [])
            return freight
            
        except Exception as e:
            raise e
    
    def list_freight_notes(self):
        """List all freight notes"""
        try:
            response = self.freight_table.scan()
            freight_notes = response.get('Items', [])
            
            # Get allocations for each freight note
            for freight in freight_notes:
                allocations_response = self.allocation_table.scan(
                    FilterExpression='freight_id = :freight_id',
                    ExpressionAttributeValues={':freight_id': freight['freight_id']}
                )
                freight['allocations'] = allocations_response.get('Items', [])
            
            # Sort by date descending
            freight_notes.sort(key=lambda x: x.get('date', ''), reverse=True)
            return freight_notes
            
        except Exception as e:
            raise e
    
    def update_freight_note(self, freight_id, transport_vendor=None, total_amount=None, date=None, allocations=None):
        """Update freight note"""
        try:
            # Get existing freight note
            existing = self.get_freight_note(freight_id)
            if not existing:
                raise ValueError("Freight note not found")
            
            update_expression = "SET updated_at = :updated_at"
            expression_values = {':updated_at': datetime.now().isoformat()}
            
            if transport_vendor:
                update_expression += ", transport_vendor = :vendor"
                expression_values[':vendor'] = transport_vendor
            
            if date:
                update_expression += ", #date = :date"
                expression_values[':date'] = date
            
            if total_amount is not None and allocations:
                # Validate allocations sum
                allocation_sum = sum(Decimal(str(allocation['amount'])) for allocation in allocations)
                if allocation_sum != Decimal(str(total_amount)):
                    raise ValueError(f"Total amount ({total_amount}) does not match sum of allocations ({allocation_sum})")
                
                update_expression += ", total_amount = :total_amount"
                expression_values[':total_amount'] = Decimal(str(total_amount))
                
                # Delete existing allocations
                for allocation in existing['allocations']:
                    self.allocation_table.delete_item(Key={'allocation_id': allocation['allocation_id']})
                
                # Create new allocations
                timestamp = datetime.now().isoformat()
                for allocation in allocations:
                    allocation_item = {
                        'allocation_id': str(uuid.uuid4()),
                        'freight_id': freight_id,
                        'supplier_name': allocation['supplier_name'],
                        'amount': Decimal(str(allocation['amount'])),
                        'created_at': timestamp
                    }
                    self.allocation_table.put_item(Item=allocation_item)
            
            # Update freight header
            self.freight_table.update_item(
                Key={'freight_id': freight_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames={'#date': 'date'} if date else None
            )
            
            return self.get_freight_note(freight_id)
            
        except Exception as e:
            raise e
    
    def delete_freight_note(self, freight_id):
        """Delete freight note and its allocations"""
        try:
            # Get existing freight note
            existing = self.get_freight_note(freight_id)
            if not existing:
                raise ValueError("Freight note not found")
            
            # Delete allocations
            for allocation in existing['allocations']:
                self.allocation_table.delete_item(Key={'allocation_id': allocation['allocation_id']})
            
            # Delete freight header
            self.freight_table.delete_item(Key={'freight_id': freight_id})
            
            return True
            
        except Exception as e:
            raise e