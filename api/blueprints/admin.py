from flask import Blueprint, jsonify, request, current_app
from firebase_admin import auth
from datetime import datetime
import os

from ...database import db
from ..utils.auth import auth_admin
from ..models.models import Admin

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/signup/', methods = ['POST'])
def admin_signup () :
    try :
        # retrieve token
        token = request.headers['Authorization'].replace('Bearer ', '')
        # decode to retrieve uid
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']

        if not uid :
            return jsonify({
                'error': 'Firebase error'
            }), 400
        
        # setting admin status on firebase claims
        auth.set_custom_user_claims(uid, { 'admin': True })
        

        # creating admin
        admin_data = {
            'name': request.json.get('name'),
            'firebase_uid': uid,
            'pin': request.json.get('pin'),
            'created_at': datetime.utcnow()
        }

        new_admin = Admin(**admin_data)

        db.session.add(new_admin) 
        db.session.commit()
        db.session.refresh(new_admin)

        # returns generated employeeId
        return jsonify({
            'employeeId': new_admin.employee_id,
            'message': 'Admin registered successfully',
        }), 201

    except Exception as error :
        current_app.logger.error(f'Error registering admin: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    

@admin_bp.route('/login', methods = ['POST'])
def admin_login () :
    try :
        # matching firebase_uid to retrieve admin
        admin = auth_admin(request)

        # match employee id and pin
        # if pin is expired prompt to update pin

        # if no match to employee id and pin, send failure and log out of firebase

    except Exception as error :
        current_app.logger.error(f'Error logging admin in: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
# @admin_bp.route('/update-pin', methods = ['POST'])
# def admin_update_pin () :

#     # retrieve admin from firebase_uid
#     admin = auth_admin(request)
#     # match employee id and old pin
#     # match new pin and confirm new pin
#     # update pin, update pin expiration
#     # return success




@admin_bp.route('/validate-code/', methods = ['POST'])
def validate_employer_code () :
    # used to validate an admin signup
        # to ensure not just any user tries to create an admin level account
    employer_code = os.getenv('EMPLOYER_CODE')
    if request.json.get('code') == employer_code :
        return jsonify({
            'message': 'Valid code'
        }), 200
    else :
        return jsonify({
            'message': 'Invalid code'
        }), 400