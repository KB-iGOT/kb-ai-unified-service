import redis
from typing import Optional, Any
import json
import os
from dotenv import load_dotenv

load_dotenv()

class RedisService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisService, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )
        self.default_expiry = int(os.getenv('REDIS_CACHE_EXPIRY', 3600))

    def set_with_expiry(self, key: str, value: Any, expiry_seconds: Optional[int] = None) -> bool:
        """Store any value in Redis with expiration time"""
        try:
            return self.redis_client.setex(
                key,
                expiry_seconds or self.default_expiry,
                json.dumps(value)
            )
        except Exception as e:
            print(f"Error setting Redis key: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis"""
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Error getting Redis key: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete a key from Redis"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            print(f"Error deleting Redis key: {e}")
            return False
