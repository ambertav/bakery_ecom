import os
import json

from cryptography.fernet import Fernet
from ...redis_config import get_redis_client

fernet = Fernet(os.getenv('FERNET_KEY').encode())

def retrieve_products (key) :
    redis_client = get_redis_client()
    cached_products = redis_client.get(key)
    return json.loads(cached_products) if cached_products else None

def store_products (key, response) :
    redis_client = get_redis_client()
    
    # expiration set for 24 hours
    redis_client.setex(key, 86400, json.dumps(response))


def encrypt_token (token) :
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token) :
    return fernet.decrypt(encrypted_token).decode()

def store_token (token, ttl) :
    redis_client = get_redis_client()

    redis_client.sadd('blacklist:tokens', encrypt_token(token))
    redis_client.expire('blacklist:tokens', ttl)

def is_token_blacklisted (token) :
    redis_client = get_redis_client()
    
    encrypted_tokens = redis_client.smembers('blacklist:tokens')

    for encrypted_token in encrypted_tokens :
        decrypted_token = decrypt_token(encrypted_token.encode())

        if decrypted_token == token :
            return True
    
    return False
