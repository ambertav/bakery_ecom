from firebase_admin import auth

from ..models.models import User

def auth_user (token) :
    # decode to retrieve uid
    decoded_token = auth.verify_id_token(token)
    uid = decoded_token['uid']

    user = User.query.filter_by(firebase_uid = uid).first()
    if not user :
        return None
    else :
        return user