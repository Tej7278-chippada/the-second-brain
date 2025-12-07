# auth/routes.py
from flask import Blueprint, request, jsonify
from .models import User
from .utils import AuthUtils, token_required
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/google', methods=['POST'])
def google_auth():
    """Google OAuth login/registration"""
    try:
        data = request.json
        token = data.get('token')
        client_id = data.get('clientId')
        
        if not token:
            return jsonify({'error': 'No token provided'}), 400
        
        # Verify token matches client ID
        if client_id != os.getenv('GOOGLE_CLIENT_ID'):
            return jsonify({'error': 'Invalid client ID'}), 403
        
        # Verify Google token
        user_info = AuthUtils.verify_google_token(token)
        if not user_info:
            return jsonify({'error': 'Invalid Google token'}), 401
        
        # Check if email is verified
        if not user_info.get('email_verified', False):
            return jsonify({'error': 'Email not verified by Google'}), 403
        
        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])
        google_id = user_info['sub']
        picture = user_info.get('picture')
        
        # Check if user exists
        user = User.find_by_email(email) or User.find_by_google_id(google_id)
        is_new_user = False
        
        if not user:
            # Create new user
            user = User.create_google_user(email, name, google_id, picture)
            is_new_user = True
        else:
            # Check account status
            if user.account_status == 'suspended':
                return jsonify({
                    'error': f'Account {email} has been suspended'
                }), 403
            
            # Update last login
            user.update_last_login()
        
        # Generate JWT token
        jwt_token = AuthUtils.create_jwt_token(user.id, user.username, user.email)
        
        return jsonify({
            'message': 'Account created' if is_new_user else 'Login successful',
            'authToken': jwt_token,
            'user': user.to_dict(),
            'isNewUser': is_new_user,
            'redirectTo': '/'
        })
        
    except Exception as e:
        print(f"Auth error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@auth_bp.route('/validate', methods=['GET'])
@token_required
def validate_token():
    """Validate JWT token"""
    user = request.user
    return jsonify({
        'valid': True,
        'user': user.to_dict()
    })

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """Logout user (client-side token removal)"""
    return jsonify({'message': 'Logged out successfully'})

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    """Get user profile"""
    user = request.user
    return jsonify({'user': user.to_dict()})