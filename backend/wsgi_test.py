"""
Simple WSGI application for testing
"""

def application(environ, start_response):
    """Simple WSGI app that returns JSON"""
    status = '200 OK'
    headers = [('Content-type', 'application/json')]
    start_response(status, headers)
    return [b'{"status": "ok", "message": "WSGI is working!"}']