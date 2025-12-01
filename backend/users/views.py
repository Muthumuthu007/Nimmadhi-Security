import hashlib
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from backend.dynamodb_service import dynamodb_service
from botocore.exceptions import ClientError
from .jwt_utils import generate_jwt_token, decode_jwt_token
from .token_manager import TokenManager
from .decorators import jwt_required

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def register_user(request):
    """Register a new user - converted from Lambda register_user function"""
    try:
        body = json.loads(request.body)
        
        if 'username' not in body or 'password' not in body:
            return JsonResponse({"error": "'username' and 'password' are required."}, status=400)
        
        username = body['username']
        password = body['password']
        
        # Check if user exists
        try:
            existing_user = dynamodb_service.get_item('USERS', {'username': username})
            if existing_user:
                return JsonResponse({"error": "Username already registered."}, status=400)
        except ClientError:
            pass
        
        # Create user with default role
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        role = body.get('role', 'user')  # Default to 'user' if not specified
        
        # Validate role
        if role not in ['admin', 'user']:
            return JsonResponse({"error": "Role must be 'admin' or 'user'."}, status=400)
        
        user_item = {
            'username': username,
            'password': hashed_password,
            'role': role
        }
        dynamodb_service.put_item('USERS', user_item)
        
        # Generate JWT token
        token = generate_jwt_token(username, role)
        
        logger.info(f"New user registered: {username}")
        return JsonResponse({
            "username": username,
            "password": "[HIDDEN]",
            "role": role,
            "token": token,
            "message": "User registered successfully."
        })
        
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def login_user(request):
    """User login - converted from Lambda login_user function"""
    try:
        body = json.loads(request.body)
        
        if 'username' not in body or 'password' not in body:
            return JsonResponse({"error": "'username' and 'password' are required."}, status=400)
        
        username = body['username']
        password = body['password']
        
        # Get user from DynamoDB
        try:
            user = dynamodb_service.get_item('USERS', {'username': username})
            if not user:
                return JsonResponse({"error": "Invalid username or password."}, status=401)
            
            hashed_input_password = hashlib.sha256(password.encode()).hexdigest()
            if hashed_input_password != user['password']:
                return JsonResponse({"error": "Invalid username or password."}, status=401)
        except ClientError:
            return JsonResponse({"error": "Invalid username or password."}, status=401)
        
        # Generate JWT token
        role = user.get('role', 'user')
        token = generate_jwt_token(username, role)
        
        logger.info(f"User logged in: {username}")
        return JsonResponse({
            "username": username,
            "password": "[HIDDEN]",
            "role": role,
            "token": token,
            "message": "Login successful."
        })
        
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def admin_view_users(request):
    """Admin view all users - converted from Lambda admin_view_users function"""
    try:
        body = json.loads(request.body)
        
        # Admin auth check
        username = body.get('username')
        password = body.get('password')
        
        if not username or not password:
            return JsonResponse({"error": "Username and password required."}, status=400)
        
        # Verify admin credentials from DynamoDB
        try:
            user = dynamodb_service.get_item('USERS', {'username': username})
            if not user or user.get('role') != 'admin':
                return JsonResponse({"error": "Unauthorized: Admin access required."}, status=403)
            
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if hashed_password != user['password']:
                return JsonResponse({"error": "Unauthorized: Invalid credentials."}, status=403)
        except ClientError:
            return JsonResponse({"error": "Unauthorized: Admin access required."}, status=403)
        
        # Get all users from DynamoDB
        try:
            users = dynamodb_service.scan_table('USERS')
            # Remove password from response for security
            for user in users:
                user.pop('password', None)
            logger.info("Admin viewed all users.")
            return JsonResponse(users, safe=False)
        except ClientError as e:
            logger.error(f"Error fetching users: {e}")
            return JsonResponse({"error": "Failed to fetch users"}, status=500)
        
    except Exception as e:
        logger.error(f"Error in admin_view_users: {str(e)}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def admin_update_user(request):
    """Admin update user - converted from Lambda admin_update_user function"""
    try:
        body = json.loads(request.body)
        
        # Admin auth check
        username = body.get('username')
        password = body.get('password')
        
        if not username or not password:
            return JsonResponse({"error": "Username and password required."}, status=400)
        
        # Verify admin credentials from DynamoDB
        try:
            user = dynamodb_service.get_item('USERS', {'username': username})
            if not user or user.get('role') != 'admin':
                return JsonResponse({"error": "Unauthorized: Admin access required."}, status=403)
            
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if hashed_password != user['password']:
                return JsonResponse({"error": "Unauthorized: Invalid credentials."}, status=403)
        except ClientError:
            return JsonResponse({"error": "Unauthorized: Admin access required."}, status=403)
        
        if 'username_to_update' not in body:
            return JsonResponse({"error": "'username_to_update' is required"}, status=400)
        
        username_to_update = body['username_to_update']
        new_password = body.get('new_password')
        new_role = body.get('new_role')
        
        # Validate role if provided
        if new_role and new_role not in ['admin', 'user']:
            return JsonResponse({"error": "Role must be 'admin' or 'user'."}, status=400)
        
        # Check if user exists and update
        try:
            user = dynamodb_service.get_item('USERS', {'username': username_to_update})
            if not user:
                return JsonResponse({"error": f"User '{username_to_update}' not found."}, status=404)
            
            update_parts = []
            expression_values = {}
            
            if new_password:
                hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                update_parts.append('password = :password')
                expression_values[':password'] = hashed_password
            
            if new_role:
                update_parts.append('#role = :role')
                expression_values[':role'] = new_role
            
            if update_parts:
                update_expression = 'SET ' + ', '.join(update_parts)
                kwargs = {}
                if new_role:
                    kwargs['ExpressionAttributeNames'] = {'#role': 'role'}
                
                dynamodb_service.update_item(
                    'USERS',
                    {'username': username_to_update},
                    update_expression,
                    expression_values,
                    **kwargs
                )
        except ClientError as e:
            logger.error(f"Error updating user: {e}")
            return JsonResponse({"error": "Failed to update user"}, status=500)
        
        logger.info(f"Admin updated user '{username_to_update}'.")
        return JsonResponse({"message": f"User '{username_to_update}' updated successfully."})
        
    except Exception as e:
        logger.error(f"Error in admin_update_user: {str(e)}")
        return JsonResponse({"error": f"Internal error: {str(e)}"}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def logout_user(request):
    """Logout user by blacklisting token"""
    try:
        token = request.jwt_token
        if TokenManager.blacklist_token(token):
            logger.info(f"User logged out: {request.user_info.get('username')}")
            return JsonResponse({"message": "Logged out successfully"})
        else:
            return JsonResponse({"error": "Logout failed"}, status=500)
    except Exception as e:
        logger.error(f"Error in logout_user: {e}")
        return JsonResponse({"error": "Logout failed"}, status=500)