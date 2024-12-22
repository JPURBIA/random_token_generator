from redis_client import RedisClient
from config import (
    TOKEN_POOL_KEY, ASSIGNED_TOKEN_KEY_FORMAT, FREE_TOKEN_KEY_FORMAT,
    CLEANUP_LOCK_KEY, CLEANUP_LOCK_TIMEOUT, CLEANUP_WAIT_TIME
)
import time

redisclient = RedisClient.get_client()

def initiailize_cleanup_with_lock():
    # Clean up the Redis token pool after acquiring a lock by removing tokens that no longer exist in Redis.
    
    # Attempt to acquire the lock
    if redisclient.setnx(CLEANUP_LOCK_KEY, "locked"):
        print("Running cleanup task...")
        
        redisclient.expire(CLEANUP_LOCK_KEY, CLEANUP_LOCK_TIMEOUT)
        try:
            invalid_tokens = []
            for token in redisclient.smembers(TOKEN_POOL_KEY):
                if not redisclient.exists(FREE_TOKEN_KEY_FORMAT.format(token=token)) and not redisclient.exists(ASSIGNED_TOKEN_KEY_FORMAT.format(token=token)):
                    invalid_tokens.append(token)
            
            if invalid_tokens:
                redisclient.srem(TOKEN_POOL_KEY, *invalid_tokens)
                print(f"Removed invalid tokens from pool: {invalid_tokens}")
            time.sleep(20)
        finally:
            redisclient.delete(CLEANUP_LOCK_KEY)
    else:
        print("Another instance is performing the cleanup. Waiting for the lock to be released...")
        while redisclient.exists(CLEANUP_LOCK_KEY):  # Wait until the lock is released
            time.sleep(CLEANUP_WAIT_TIME)  # Sleep for a defined interval before retrying
        print("Cleanup completed by another instance. Proceeding with app startup.")