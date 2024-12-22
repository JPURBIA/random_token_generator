# Configuration
POOL_MAX_SIZE = 5
TOKEN_LIFETIME = 60  # seconds
KEEP_ALIVE_INTERVAL = 300  # seconds
KEEP_ALIVE_BATCH_SIZE = 100 # number of tokens to process at a time for bulk update expiry

# Redis DB config
REDIS_DB = {
    "host": "localhost",
    "port": 6379,
    "db": 0
}

try:
    from local_config import *
except ImportError as e:
    print(f"Error in loading local configurations. Details: {e}")

# Token keys in Redis
TOKEN_POOL_KEY = "token_pool"  # Set of all tokens
ASSIGNED_TOKEN_KEY_FORMAT = "assign:{token}"
FREE_TOKEN_KEY_FORMAT = "pool:{token}"

