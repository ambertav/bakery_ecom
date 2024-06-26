from firebase_admin import auth

from ..models.models import User, Admin

def auth_user (request) :
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
        return error
    
        
def auth_admin (request) :
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
        return error