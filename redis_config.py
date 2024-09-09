import redis

def init_redis (url) :
    global redis_client
    redis_client = redis.StrictRedis.from_url(url, decode_responses = True)

def get_redis_client () :
    if redis_client is None :
        raise RuntimeError('Redis client has not initialized')
    
    return redis_client