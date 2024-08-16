import random
from datetime import datetime, timedelta, timezone
import bcrypt

from ...database import db


class Admin (db.Model) :
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key = True)
    employee_id = db.Column(db.Integer, unique = True, nullable = False)
    pin = db.Column(db.String(72), nullable = False)
    pin_expiration = db.Column(db.DateTime(timezone = True), nullable = False)
    name = db.Column(db.String(30), nullable = False)
    firebase_uid = db.Column(db.String(128), nullable = False)
    created_at = db.Column(db.DateTime(timezone = True), nullable = False)

    tasks = db.relationship('Task', backref = 'admin', lazy = 'dynamic')

    def __init__ (self, pin, name, firebase_uid, created_at) :
        self.pin = self.hash_pin(pin) # store hash of pin
        self.name = name
        self.firebase_uid = firebase_uid
        self.created_at = created_at

        # generate unique employee id
        self.employee_id = self._generate_unique_employee_id()

        # setting initial pin expiration to 30 days after creation
        self.pin_expiration = self.created_at + timedelta(days = 30)

    def _generate_unique_employee_id (self) :
        # generating random 8 digit number
        id = random.randint(10000000, 99999999)
        
        # checking if employee_id already exists in database
        while Admin.query.filter_by(employee_id = id).first() :
            id = random.randint(10000000, 99999999)
        
        return id
    
    def hash_pin (self, pin) :
        # ensuring max of 5 digits
        pin = str(pin)[:5]

        # generate salt and return hash
        salt = bcrypt.gensalt(12)
        return bcrypt.hashpw(pin.encode(), salt)
    
    def check_pin (self, pinInput) :
        return bcrypt.checkpw(str(pinInput).encode(), self.pin)
    
    def is_pin_expired (self) :
        # checking pin expiration
        return datetime.now(timezone.utc) > self.pin_expiration

    def renew_pin (self, old_pin, new_pin) :

        # if the old pin matches stored pin
        if bcrypt.checkpw(str(old_pin).encode(), self.pin) :
            # renew pin and update pin expiration date (30 days from current time)
            self.pin = self.hash_pin(new_pin)
            self.pin_expiration = datetime.now(timezone.utc) + timedelta(days = 30)
            
            return True
        else :
            # else return false to indicate wrong input of old pin
            return False