# auth/utils.py
import os
import jwt
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from functools import wraps
from flask import jsonify, request

class AuthUtils:
    @staticmethod
    def create_jwt_token(user_id, username, email):
        """Create JWT token"""
        payload = {
            'sub': user_id,
            'username': username,
            'email': email,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, os.getenv('JWT_SECRET'), algorithm='HS256')
    
    @staticmethod
    def verify_jwt_token(token):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def verify_google_token(token):
        """Verify Google OAuth token"""
        try:
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                os.getenv('GOOGLE_CLIENT_ID')
            )
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            return idinfo
        except Exception as e:
            print(f"Google token verification failed: {e}")
            return None

def token_required(f):
    """Decorator to protect routes with JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({
                'error': 'Authentication required',
                'redirect': '/login'
            }), 401
        
        # Verify token
        payload = AuthUtils.verify_jwt_token(token)
        if not payload:
            return jsonify({
                'error': 'Invalid or expired token',
                'redirect': '/login'
            }), 401
        
        # Get user from database
        from .models import User
        user = User.find_by_id(payload['sub'])
        
        if not user or user.account_status != 'active':
            return jsonify({
                'error': 'User not found or inactive',
                'redirect': '/login'
            }), 401
        
        # Add user to request context
        request.user = user
        request.user_id = user.id
        
        return f(*args, **kwargs)
    
    return decorated