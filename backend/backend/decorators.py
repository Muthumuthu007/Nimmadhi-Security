from functools import wraps

def no_cache(view_func):
    """
    Decorator to add no-cache headers to view responses.
    Use this on individual views if needed for extra enforcement.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    return wrapper
