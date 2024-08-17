from flask import Blueprint, jsonify, request, current_app
from firebase_admin import auth
from datetime import datetime, timezone
import os

from ...database import db
from ..utils.auth import auth_admin
from ..models import Admin

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/signup/', methods = ['POST'])
def admin_signup () :
    '''
    Registers a new admin user.

    Retrieves the Firebase token from the request headers, decodes to get user's UID, and creates a new admin
    record in the database.

    Request Body :
        - name (str) : name of admin.
        - pin (str) : PIN for admin account.
    
    Returns :
        Response : JSON response with admin's employee id and a success message or an error message.
    '''
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
        # auth.set_custom_user_claims(uid, { 'admin': True })
        

        # creating admin
        admin_data = {
            'name': request.json.get('name'),
            'firebase_uid': uid,
            'pin': request.json.get('pin'),
            'created_at': datetime.now(timezone.utc)
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
    

@admin_bp.route('/login/', methods = ['POST'])
def admin_login () :
    '''
    Logs in an existing admin.

    Authenticates an admin by matching provided employee ID and PIN, checking if PIN is valid and not expired.

    Request Body :
        - employeeId (str) : requesting admin's employee ID.
        - pin (str) : requesting admin's PIN.

    Returns :
        Response : JSON response containing a sucess or error message.
    '''
    try :
        # matching firebase_uid to retrieve admin
        admin = auth_admin(request)

        # match employee id and pin
        if str(admin.employee_id) == request.json.get('employeeId') and admin.check_pin(request.json.get('pin')) :
            # if pin is expired prompt to update pin
            if not admin.is_pin_expired() :
                return jsonify({
                    'message': 'Admin logged in successfully',
                }), 200
            else :
                return jsonify({
                    'message': 'Pin is expired, please renew pin',
                }), 403
        else :
            # if no match to employee id and pin, send failure and prompt to log out of firebase
            return jsonify({
                'error': 'Invalid credientials',
            }), 401

    except Exception as error :
        current_app.logger.error(f'Error logging admin in: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
@admin_bp.route('/update-pin/', methods = ['POST'])
def admin_update_pin () :
    '''
    Updates the requesting admin's PIN.

    Validates the provided employee ID and old PIN, updates the PIN and sets a new expiration date.

    Request Body :
        - employeeId (str) : requesting admin's employee ID.
        - oldPin (str) : requesting admin's PIN.
        - pin (str) : new PIN to update.

    Returns :
        Response : JSON response containing a sucess or error message.
    '''
    try :
        # retrieve admin from firebase_uid
        admin = auth_admin(request)

        data = request.get_json()

        # match employee id and old pin, then renew and update pin_expiration date
        if str(admin.employee_id) == data.get('employeeId') and admin.renew_pin(data.get('oldPin'), data.get('pin')) :
            # commit changes to admin only if both conditions are true
            db.session.commit()
            return jsonify({
                'message': 'Pin was updated and admin logged in successfully',
            }), 200
        else :
            db.session.rollback()
            return jsonify({
                'error': 'Invalid credientials',
            }), 401
        
    except Exception as error :
        current_app.logger.error(f'Error updating pin and logging admin in: {str(error)}')
        return jsonify({
            'error': 'Internal server error'
        }), 500


@admin_bp.route('/validate-code/', methods = ['POST'])
def validate_employer_code () :
    '''
    Validates the employer code for admin signup

    Checks if the provided code matches the stored employer code, authorizing the creation of admins

    Request Body :
        code (str) : employer code

    Returns :
        Response : JSON response indicating whether the code is valid or not.
    '''
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