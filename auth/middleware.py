# auth/middleware.py
from functools import wraps
from flask import jsonify, request
from .utils import AuthUtils
from .models import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Authentication token is missing',
                'redirect': '/login'
            }), 401
        
        # Verify token
        payload = AuthUtils.verify_jwt_token(token)
        if not payload:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token',
                'redirect': '/login'
            }), 401
        
        # Get user from database
        user = User.find_by_id(payload['sub'])
        if not user or user.account_status != 'active':
            return jsonify({
                'success': False,
                'error': 'User not found or account inactive',
                'redirect': '/login'
            }), 401
        
        # Add user to request context
        request.user = user
        request.user_id = user.id
        
        return f(*args, **kwargs)
    
    return decorated

def optional_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if token:
            payload = AuthUtils.verify_jwt_token(token)
            if payload:
                user = User.find_by_id(payload['sub'])
                if user and user.account_status == 'active':
                    request.user = user
                    request.user_id = user.id
        
        return f(*args, **kwargs)
    
    return decorated