from firebase_admin import auth

from ..models import User, Admin

def auth_user (request) :
    '''
    Authenticates user using Firebase ID provided in request headers

    Extracts and verifies Firebase ID token from 'Authorization; header, and retrieves
    associated user from database. If an associated user is not found, None is returned.

    Args :
        request (Request) : incoming Flask request containing 'Authorization' header with token.

    Returns :
        User : authenticated user object if found
        None : if the user is not found or if there is an issue with token.

    Raises :
        ValueError : if there is an error suring token verification or user retrieval
    '''

    if 'Authorization' not in request.headers :
        return None
    
    try :
        # decode to retrieve uid
        token = request.headers['Authorization'].replace('Bearer ', '')
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']

        user = User.query.filter_by(firebase_uid = uid).first()

        if not user :
            return None
        else :
            return user
        
    except Exception as error :
        raise ValueError(f'Authentication failed: {str(error)}')
    
        
def auth_admin (request) :
    '''
    Authenticates admin using Firebase ID provided in request headers

    Extracts and verifies Firebase ID token from 'Authorization; header, and retrieves
    associated admin from database. If an associated admin is not found, None is returned.

    Args :
        request (Request) : incoming Flask request containing 'Authorization' header with token.

    Returns :
        Admin : authenticated admin object if found
        None : if the admin is not found or if there is an issue with token.

    Raises :
        ValueError : if there is an error suring token verification or user retrieval
    '''
    
    if 'Authorization' not in request.headers :
        return None
    
    try :
        # decode to retrieve uid
        token = request.headers['Authorization'].replace('Bearer ', '')
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']

        admin = Admin.query.filter_by(firebase_uid = uid).first()

        if not admin :
            return None
        else :
            return admin
        
    except Exception as error :
        raise ValueError(f'Authentication failed: {str(error)}')