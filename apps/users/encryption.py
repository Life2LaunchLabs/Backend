"""
Privacy and encryption utilities for user data
Provides secure encryption/decryption for sensitive PII
"""
import base64
import json
import os
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class UserDataEncryption:
    """
    Handles encryption/decryption of sensitive user data
    Uses Fernet (symmetric encryption) for PII
    """
    
    def __init__(self):
        self.encryption_key = self._get_encryption_key()
        self.cipher = Fernet(self.encryption_key)
    
    def _get_encryption_key(self):
        """
        Get encryption key from environment or generate one
        In production, this should come from secure key management
        """
        key = getattr(settings, 'USER_DATA_ENCRYPTION_KEY', None)
        if not key:
            # For development - generate a key (NOT for production!)
            key = Fernet.generate_key()
            print(f"⚠️  Generated encryption key for development: {key.decode()}")
            print("⚠️  Set USER_DATA_ENCRYPTION_KEY in production settings!")
        
        if isinstance(key, str):
            key = key.encode()
        
        return key
    
    def encrypt_user_pii(self, data_dict):
        """
        Encrypt a dictionary of user PII data
        Args:
            data_dict: Dictionary containing sensitive user data
        Returns:
            Encrypted string that can be stored in database
        """
        if not data_dict:
            return None
        
        json_data = json.dumps(data_dict, default=str)
        encrypted_data = self.cipher.encrypt(json_data.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_user_pii(self, encrypted_data):
        """
        Decrypt user PII data
        Args:
            encrypted_data: Base64 encoded encrypted string
        Returns:
            Dictionary containing decrypted user data
        """
        if not encrypted_data:
            return {}
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.cipher.decrypt(encrypted_bytes)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            # Log error in production
            print(f"Error decrypting user data: {e}")
            return {}
    
    def encrypt_field(self, value):
        """
        Encrypt a single field value
        Args:
            value: String value to encrypt
        Returns:
            Encrypted string
        """
        if not value:
            return None
        
        encrypted_data = self.cipher.encrypt(value.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_field(self, encrypted_value):
        """
        Decrypt a single field value
        Args:
            encrypted_value: Base64 encoded encrypted string
        Returns:
            Decrypted string
        """
        if not encrypted_value:
            return None
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_value.encode())
            return self.cipher.decrypt(encrypted_bytes).decode()
        except Exception as e:
            print(f"Error decrypting field: {e}")
            return None


# Global instance for easy access
user_encryption = UserDataEncryption()


def anonymize_for_logging(data):
    """
    Create anonymized version of data for logging/debugging
    Replaces PII with anonymous identifiers
    """
    if isinstance(data, dict):
        anonymized = {}
        for key, value in data.items():
            if key in ['first_name', 'last_name', 'middle_name', 'email']:
                anonymized[key] = f"[REDACTED_{key.upper()}]"
            elif key == 'username':
                anonymized[key] = f"user_{hash(value) % 10000:04d}"
            else:
                anonymized[key] = value
        return anonymized
    return data