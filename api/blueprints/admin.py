from flask import Blueprint, jsonify, request, current_app, make_response
import os

from ...database import db
from ..utils.token import generate_jwt
from ..utils.auth import auth_admin
from ..models import Admin, Role

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/signup/', methods = ['POST'])
def admin_signup () :
    '''
    Registers a new admin user.

    Request Body :
        - name (str) : name of admin.
        - email (str) : email of admin.
        - password (str) : password of admin.
        - pin (str) : PIN for admin account.
    
    Returns :
        Response : JSON response with admin's employee id and a success message or an error message.
    '''
    try :
        data = request.json

        admin_data = {
            'name': data.get('name'),
            'email': data.get('email'),
            'password': data.get('password'),
            'pin': data.get('pin'),
        }

        new_admin = Admin(**admin_data)

        db.session.add(new_admin) 
        db.session.commit()

        # returns generated employee_id
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

    Authenticates an admin by matching provided employee ID, password, PIN, checking if both the password and PIN is valid and not expired.

    Request Body :
        - employeeId (str) : requesting admin's employee ID.
        - password (str) : request admin's password.
        - pin (str) : requesting admin's PIN.

    Returns :
        Response : JSON response containing a sucess or error message.
    '''
    try :
        data = request.json

        admin = Admin.query.filter_by(employee_id = data.get('employeeId')).first()

        # match employee id and pin
        if admin and admin.verify_password(data.get('password')) and admin.check_pin(data.get('pin')) :
            # if pin is expired prompt to update pin
            if not admin.is_password_expired() :

                token = generate_jwt(admin.id)
                response = make_response(
                    jsonify({
                        'message': 'Admin logged in successfully',
                    }), 200
                )

                response.set_cookie(
                    'access_token',
                    value = token,
                    httponly = 'true',
                    max_age = 60 * 60 * 24 * 7,
                    samesite = 'None',
                    secure = 'false'
                )

                return response
            
            else :
                return jsonify({
                    'message': 'Password is expired, please renew password',
                }), 403
        else :
            # if no match to password and pin, send failure
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