import os
import sys
import logging

logger = logging.getLogger(__name__)

class ConfigValidator:
    REQUIRED_SETTINGS = [
        'DJANGO_SECRET_KEY',
        'JWT_SECRET',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY'
    ]
    
    PRODUCTION_SETTINGS = [
        'ALLOWED_HOSTS',
        'CSRF_TRUSTED_ORIGINS'
    ]
    
    @staticmethod
    def validate_environment():
        """Validate environment configuration"""
        errors = []
        warnings = []
        
        # Check required settings
        for setting in ConfigValidator.REQUIRED_SETTINGS:
            value = os.environ.get(setting)
            if not value:
                errors.append(f"Missing required environment variable: {setting}")
            elif setting in ['DJANGO_SECRET_KEY', 'JWT_SECRET'] and len(value) < 32:
                warnings.append(f"{setting} should be at least 32 characters long")
        
        # Check production settings
        debug = os.environ.get('DEBUG', 'True').lower() == 'true'
        if not debug:
            for setting in ConfigValidator.PRODUCTION_SETTINGS:
                value = os.environ.get(setting)
                if not value:
                    warnings.append(f"Production setting not configured: {setting}")
        
        # Check for default/insecure values
        secret_key = os.environ.get('DJANGO_SECRET_KEY', '')
        if 'django-insecure' in secret_key:
            errors.append("DJANGO_SECRET_KEY contains 'django-insecure' - change for production")
        
        jwt_secret = os.environ.get('JWT_SECRET', '')
        if jwt_secret in ['your-secret-key-change-in-production', 'your-jwt-secret-key-change-this']:
            errors.append("JWT_SECRET is using default value - change for production")
        
        # Log results
        if errors:
            for error in errors:
                logger.error(f"Configuration Error: {error}")
            if not debug:
                sys.exit("Critical configuration errors found. Exiting.")
        
        if warnings:
            for warning in warnings:
                logger.warning(f"Configuration Warning: {warning}")
        
        if not errors and not warnings:
            logger.info("Configuration validation passed")
        
        return len(errors) == 0

# Validate on import
ConfigValidator.validate_environment()