import redis
from config import REDIS_DB

class RedisClient:
    __client = None

    @staticmethod
    def get_client():
        if RedisClient.__client is None:
            RedisClient.__client = redis.StrictRedis(
                host=REDIS_DB["host"],
                port=REDIS_DB["port"],
                db=REDIS_DB["db"],
                decode_responses=True
            )
        return RedisClient.__client