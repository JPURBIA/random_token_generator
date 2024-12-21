import threading, signal
from config import TOKEN_POOL_KEY, FREE_TOKEN_KEY_FORMAT, ASSIGNED_TOKEN_KEY_FORMAT
from redis_client import RedisClient

shutdown_flag = threading.Event()
redisclient = RedisClient.get_client()

# Function to listen for key expiry events
def listen_for_expirations():
    pubsub = redisclient.pubsub()
    pubsub.psubscribe('__keyevent@0__:expired')  # Listen for expired keys
    assigned_key_prefix = ASSIGNED_TOKEN_KEY_FORMAT.replace("{token}", "")
    pool_key_prefix = FREE_TOKEN_KEY_FORMAT.replace("{token}", "")
    try:
        for message in pubsub.listen():
            if message['type'] == 'pmessage':
                expired_key = message['data']
                if expired_key.startswith(pool_key_prefix):  # Check if the expired key is a token
                    token = expired_key.split(":")[1]
                    print(f"Token expired: {token}")
                    # Remove expired token from the pool
                    redisclient.srem(TOKEN_POOL_KEY, token)
                elif expired_key.startswith(assigned_key_prefix):  # Check if the expired key is a token
                    token = expired_key.split(":")[1]
                    print(f"Assigned token expired: {token}, adding it to pool")
                    # Remove expired token from the pool
                    redisclient.sadd(TOKEN_POOL_KEY, token)
    finally:
        pubsub.close()

def handle_exit(signum, frame):
    shutdown_flag.set()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    # Start a thread for listening to Redis key expirations
    listener_thread = threading.Thread(target=listen_for_expirations, daemon=True).start()

    while True:
        if shutdown_flag.is_set():
            print("Listener stopped.")
            break