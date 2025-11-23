import uuid
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from .models import StockTransaction, UndoAction

logger = logging.getLogger(__name__)

def log_transaction(operation, details, username):
    """Log transaction exactly as in Lambda"""
    transaction_id = str(uuid.uuid4())
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    date_str = now.strftime("%Y-%m-%d")

    # Convert floats to Decimal
    for k, v in list(details.items()):
        if isinstance(v, float):
            details[k] = Decimal(str(v))
    details['username'] = username

    try:
        StockTransaction.objects.create(
            transaction_id=transaction_id,
            operation_type=operation,
            details=details,
            date=date_str,
            timestamp=now
        )
        logger.info(f"Transaction logged: {operation} (ID: {transaction_id})")
    except Exception as e:
        logger.error(f"Error in log_transaction: {e}")
        raise

def get_user_active_undo_count(username):
    """Get count of active undo records for user"""
    try:
        return UndoAction.objects.filter(username=username, status='ACTIVE').count()
    except Exception as e:
        logger.error(f"Error in get_user_active_undo_count: {str(e)}")
        return 0

def remove_oldest_undo(username):
    """Remove oldest undo record for user"""
    try:
        oldest = UndoAction.objects.filter(
            username=username, 
            status='ACTIVE'
        ).order_by('timestamp').first()
        if oldest:
            oldest.delete()
            logger.info(f"Removed oldest undo record for user {username}: {oldest.undo_id}")
    except Exception as e:
        logger.error(f"Error in remove_oldest_undo: {str(e)}")

def log_undo_action(operation, undo_details, username):
    """Log undo action exactly as in Lambda"""
    try:
        if get_user_active_undo_count(username) >= 3:
            remove_oldest_undo(username)
            
        undo_id = str(uuid.uuid4())
        timestamp = datetime.utcnow() + timedelta(hours=5, minutes=30)
        
        UndoAction.objects.create(
            undo_id=undo_id,
            operation=operation,
            undo_details=undo_details,
            username=username,
            status='ACTIVE',
            timestamp=timestamp
        )
        logger.info(f"Undo record logged: {operation}, ID: {undo_id}")
        return undo_id
    except Exception as e:
        logger.error(f"Error in log_undo_action: {str(e)}")
        return None

def mark_undo_as_done(undo_id):
    """Mark undo record as done"""
    try:
        undo_action = UndoAction.objects.get(undo_id=undo_id)
        undo_action.status = 'UNDONE'
        undo_action.save()
    except Exception as e:
        logger.error(f"Error in mark_undo_as_done: {str(e)}")

def get_undo_record(undo_id):
    """Get undo record by ID"""
    try:
        undo_action = UndoAction.objects.get(undo_id=undo_id)
        return {
            'undo_id': undo_action.undo_id,
            'operation': undo_action.operation,
            'undo_details': undo_action.undo_details,
            'username': undo_action.username,
            'status': undo_action.status,
            'timestamp': undo_action.timestamp.isoformat()
        }
    except UndoAction.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error in get_undo_record: {str(e)}")
        return None