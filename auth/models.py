# auth/models.py
from datetime import datetime
import bcrypt
import jwt
import os
from bson import ObjectId
from pymongo import MongoClient
import secrets

# MongoDB connection
client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
db = client['secondbrain']
users_collection = db['users']

class User:
    def __init__(self, user_data=None):
        self.id = str(user_data['_id']) if user_data and '_id' in user_data else None
        self.username = user_data.get('username') if user_data else None
        self.email = user_data.get('email') if user_data else None
        self.google_id = user_data.get('google_id') if user_data else None
        self.profile_pic = user_data.get('profile_pic') if user_data else None
        self.account_status = user_data.get('account_status', 'active') if user_data else 'active'
        self.user_role = user_data.get('user_role', 'user') if user_data else 'user'
        self.created_at = user_data.get('created_at', datetime.utcnow()) if user_data else datetime.utcnow()
        self.last_login = user_data.get('last_login', datetime.utcnow()) if user_data else datetime.utcnow()
        
    @staticmethod
    def generate_user_code():
        """Generate unique user code"""
        timestamp = datetime.utcnow().strftime('%y%m%d%H%M')
        random_part = secrets.token_hex(3).upper()
        return f"SB{timestamp}{random_part}"
    
    @classmethod
    def find_by_email(cls, email):
        """Find user by email"""
        user_data = users_collection.find_one({'email': email})
        return cls(user_data) if user_data else None
    
    @classmethod
    def find_by_google_id(cls, google_id):
        """Find user by Google ID"""
        user_data = users_collection.find_one({'google_id': google_id})
        return cls(user_data) if user_data else None
    
    @classmethod
    def find_by_id(cls, user_id):
        """Find user by ID"""
        try:
            user_data = users_collection.find_one({'_id': ObjectId(user_id)})
            return cls(user_data) if user_data else None
        except:
            return None
    
    @classmethod
    def create_google_user(cls, email, name, google_id, picture=None):
        """Create new user from Google OAuth"""
        # Generate unique username
        base_username = name.lower().replace(' ', '')[:15]
        username = base_username
        counter = 1
        
        while users_collection.find_one({'username': username}):
            username = f"{base_username}{counter}"
            counter += 1
        
        user_data = {
            'username': username,
            'email': email,
            'google_id': google_id,
            'profile_pic': picture,
            'is_google_user': True,
            'email_verified': True,
            'account_status': 'active',
            'user_role': 'user',
            'user_code': cls.generate_user_code(),
            'created_at': datetime.utcnow(),
            'last_login': datetime.utcnow(),
            'login_method': 'google'
        }
        
        result = users_collection.insert_one(user_data)
        user_data['_id'] = result.inserted_id
        return cls(user_data)
    
    def update_last_login(self):
        """Update last login timestamp"""
        users_collection.update_one(
            {'_id': ObjectId(self.id)},
            {'$set': {'last_login': datetime.utcnow()}}
        )
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'profile_pic': self.profile_pic,
            'account_status': self.account_status,
            'user_role': self.user_role,
            'created_at': self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at
        }