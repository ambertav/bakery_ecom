from sqlalchemy import CheckConstraint

from ...database import db


class Address (db.Model) :
    '''
    Represents an address associated with a user

    Attributes :
        id (int) : unique identifier for the address.
        first_name (str) : first name of the recipient.
        last_name (str) : last name of the recipient.
        street (str) : street address
        city (str) : city of the address.
        state (str) : 2-digit abbreviation of the state.
        zip (str) : 5-digit postal code 
        default (bool) : whether this is the default address for the user.
        user_id (int) : ID of the user to whom the address belongs.
    '''
    __tablename__ = 'addresses'

    id = db.Column(db.Integer, primary_key = True)
    first_name = db.Column(db.String(50), nullable = False)
    last_name = db.Column(db.String(50), nullable = False)
    street = db.Column(db.String(255), nullable = False)
    city = db.Column(db.String(100), nullable = False)
    state = db.Column(db.String(2), nullable = False)
    zip = db.Column(db.String(5), nullable = False)
    default = db.Column(db.Boolean, nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)

    __table_args__ = (
        # ensures zip to be 5 numerical digits
        CheckConstraint("LENGTH(zip) = 5 AND zip ~ '^[0-9]{5}$'", name = 'zip_format_constraint'),
    )

    def __init__ (self, first_name, last_name, street, city, state, zip, default, user_id) :
        '''
        Initializes a new address instance.

        Args :
            first_name (str) : first name of the recipient.
            last_name (str) : last name of the recipient.
            street (str) : street address
            city (str) : city of the address.
            state (str) : 2-digit abbreviation of the state.
            zip (str) : 5-digit postal code 
            default (bool) : whether this is the default address for the user.
            user_id (int) : ID of the user to whom the address belongs.
        '''
        self.first_name = first_name
        self.last_name = last_name
        self.street = street
        self.city = city
        self.state = state
        self.zip = zip
        self.default = default
        self.user_id = user_id

    def toggle_default (self) :
        '''
        Toggles the default status of the address by setting default attribute to its opposite bool value.
        '''
        self.default = not self.default

    def as_dict (self) :
        '''
        Converts address instance to a dictionary.

        Returns : 
            dict : dictionary representation of address instance. NOTE: camelCasing for ease in frontend.
        '''
        return {
            'id': self.id,
            'firstName': self.first_name,
            'lastName': self.last_name,
            'street': self.street,
            'city': self.city,
            'state': self.state,
            'zip': self.zip,
            'default': self.default
        }