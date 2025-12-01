import time
import hashlib
from django.core.cache import cache
from .jwt_utils import decode_jwt_token
import logging

logger = logging.getLogger(__name__)

class TokenManager:
    BLACKLIST_PREFIX = "blacklisted_token_"
    
    @staticmethod
    def blacklist_token(token):
        """Add token to blacklist"""
        try:
            payload = decode_jwt_token(token)
            if payload:
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                expiry = payload.get('exp', time.time() + 3600)
                ttl = max(int(expiry - time.time()), 0)
                
                cache.set(f"{TokenManager.BLACKLIST_PREFIX}{token_hash}", True, ttl)
                logger.info(f"Token blacklisted for user: {payload.get('username')}")
                return True
        except Exception as e:
            logger.error(f"Error blacklisting token: {e}")
        return False
    
    @staticmethod
    def is_token_blacklisted(token):
        """Check if token is blacklisted"""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            return cache.get(f"{TokenManager.BLACKLIST_PREFIX}{token_hash}", False)
        except Exception:
            return False
    
    @staticmethod
    def cleanup_expired_tokens():
        """Cleanup expired blacklisted tokens (called by cron job)"""
        # Cache automatically handles TTL, no manual cleanup needed
        pass