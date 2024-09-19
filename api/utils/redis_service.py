import os
import json

from cryptography.fernet import Fernet
from ...redis_config import get_redis_client

fernet = Fernet(os.getenv('FERNET_KEY').encode())

def need_product_bucket () :
    '''
    Checks if any keys with 'all_products' exists in cache using scan.
    Indicates whether a new cache of all the products needs to be created.

    Returns :
        bool : True is no 'all_products*' keys are found, False otherwise.
    '''
    redis_client = get_redis_client()

    while True :
        cursor, keys = redis_client.scan(cursor = 0, match = 'all_products*', count = 100)

        # indicates that a key was found
        if keys :
            return False
        
        # indicates scan is finished
        if cursor == 0 :
            break

    return True

def cache_products (products) :
    '''
    Caches a list of products, storing each product as a JSON string with the key format of 'all_products:product.id'.
    Sets the expiration for each cache entry to 1 hour.

    Args :
        products (list) : list of product objects from database to be cached.
    '''
    redis_client = get_redis_client()
    
    with redis_client.pipeline() as pipe :
        for product in products :
            pipe.set(f'all_products:{product.id}', json.dumps(product.as_dict()), ex = 3600)

        pipe.execute()

def get_filtered_products (key) :
    '''
    Retrieves a filtered list of products from cache based on provided filter parameters (indicated in key).
    
    Gets list of product ids and pagination metadata (needed for the response) from cache using key and retrieves
    the product data from the 'all_products*' cache.

    Args :
        key (str) : cache key for retrieving filtered products, indicates what page, sort and filter.

    Returns :
        dict : dictionary containing list of products and pagination metadata
        None : if no product ids or metadata found in cache from given key.
    '''
    redis_client = get_redis_client()

    product_ids = redis_client.get(key)
    metadata = redis_client.get(f'{key}:metadata')

    products = []

    if product_ids and metadata :
        for id in json.loads(product_ids) :
            product = redis_client.get(f'product:{id}')
            if product :
                products.append(json.loads(product))
        
        return {
            'products': products,
            'totalPages': json.loads(metadata).get('totalPages'),
            'currentPage': json.loads(metadata).get('currentPage')
        } if products else None
    
    return None

def cache_filtered_products (key, response) :
    '''
    Caches the results of a filtered product query.

    Stores list of product ids and pagination metadata under given key.

    Args :
        key (str) : cache key for storing filtered products, indicates what page, sort and filter.
        response (dict) : dictionary containing list of products and pagination metadata.
    '''
    redis_client = get_redis_client()
    product_ids = [product['id'] for product in response['products']]
    metadata = {
        'totalPages': response['totalPages'],
        'currentPage': response['currentPage']
    }

    with redis_client.pipeline() as pipe :
        pipe.set(key, json.dumps(product_ids))
        pipe.set(f'{key}:metadata', json.dumps(metadata))

        pipe.execute()



def encrypt_token (token) :
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token) :
    return fernet.decrypt(encrypted_token).decode()

def cache_token (token, ttl) :
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
