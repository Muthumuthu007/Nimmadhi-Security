# No Django auth decorators - using DynamoDB JWT authentication
from functools import wraps
from django.http import JsonResponse

def jwt_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # JWT validation would go here using DynamoDB
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Admin role validation would go here using DynamoDB
        return view_func(request, *args, **kwargs)
    return wrapper