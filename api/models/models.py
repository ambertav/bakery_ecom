from ...database import db
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, TIMESTAMP, ForeignKey
from enum import Enum

def serialize_enum (enum_value) :
    return enum_value.value.lower()

# Product
class Product (db.Model) :
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(80), nullable = False)
    description = db.Column(db.Text(), nullable = False)
    image = db.Column(db.String(), nullable = False)
    price = db.Column(db.Numeric(precision = 5, scale = 2), nullable = False)
    stock = db.Column(db.Integer(), nullable = False)


    def __init__ (self, name, description, image, price, stock) :
        self.name = name
        self.description = description
        self.image = image
        self.price = price
        self.stock = stock
    
    def as_dict (self) : 
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'image': self.image,
            'price': self.price,
            'stock': self.stock
        }

# enum for user role
class Role (Enum) :
    CLIENT = 'CLIENT'
    ADMIN = 'ADMIN'

# User
class User (db.Model) :
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(30), nullable = False)
    firebase_uid = db.Column(db.String(128), nullable = False)
    stripe_customer_id = db.Column(db.String(), nullable = True)
    role = db.Column(db.Enum(Role), nullable = False)
    created_at = db.Column(db.TIMESTAMP(), nullable = False)

    addresses = db.relationship('Address', backref = 'user', lazy = 'dynamic')

    def __init__ (self, name, firebase_uid, stripe_customer_id, billing_address, shipping_address, role, created_at) :
        self.name = name
        self.firebase_uid = firebase_uid
        self.stripe_customer_id = stripe_customer_id
        self.billing_address = billing_address
        self.shipping_address = shipping_address
        self.role = role
        self.created_at = created_at

# Address
class Address (db.Model) :
    __tablename__ = 'addresses'

    id = db.Column(db.Integer, primary_key = True)
    first_name = db.Column(db.String(50), nullable = False)
    last_name = db.Column(db.String(50), nullable = False)
    street = db.Column(db.String(255), nullable = False)
    city = db.Column(db.String(100), nullable = False)
    state = db.Column(db.String(2), nullable = False)
    zip = db.Column(db.String(10), nullable = False)
    default = db.Column(db.Boolean, nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)

    def __init__ (self, first_name, last_name, street, city, state, zip, default, user_id) :
        self.first_name = first_name
        self.last_name = last_name
        self.street = street
        self.city = city
        self.state = state
        self.zip = zip
        self.default = default
        self.user_id = user_id

    def as_dict (self) :
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


# Cart_item
class Cart_Item (db.Model) :
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable = False)
    product_id = db.Column(db.Integer, ForeignKey('products.id'), nullable = False)
    quantity = db.Column(db.Integer(), nullable = False)
    ordered = db.Column(db.Boolean(), default = False, nullable = False)

    # define relationships
    user = db.relationship('User', backref = 'cart_items')
    product = db.relationship('Product', backref = 'cart_items')

    def __init__ (self, user_id, product_id, quantity, ordered) :
        self.user_id = user_id
        self.product_id = product_id
        self.quantity = quantity
        self.ordered = ordered

    def as_dict (self) :
        return {
            'id': self.id,
            'productId': self.product.id,
            'name': self.product.name,
            'image': self.product.image,
            'price': self.product.price,
            'quantity': self.quantity
        }
    
# enums for order model
class Order_Status (Enum) :
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    SHIPPED = 'SHIPPED'
    DELIVERED = 'DELIVERED'
    CANCELLED = 'CANCELLED'

class Ship_Method (Enum) :
    STANDARD = 'STANDARD'
    EXPRESS = 'EXPRESS'
    NEXT_DAY = 'NEXT_DAY'


class Pay_Status (Enum) :
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

# order and cart_items assocation table
order_cart_items = db.Table(
    'order_cart_items',
    db.Column('order_id', db.Integer, db.ForeignKey('orders.id'), primary_key = True),
    db.Column('cart_item_id', db.Integer, db.ForeignKey('cart_items.id'), primary_key = True),
)

# Order
class Order (db.Model) :
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable = False)
    total_price = db.Column(db.Numeric(precision = 10, scale = 2), nullable = False)
    date = db.Column(db.TIMESTAMP(), nullable = False)
    status = db.Column(db.Enum(Order_Status), nullable = False)
    stripe_payment_id = db.Column(db.String, nullable = True)
    shipping_method = db.Column(db.Enum(Ship_Method), nullable = False)
    payment_status = db.Column(db.Enum(Pay_Status), nullable = False)
    shipping_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id', ondelete = 'RESTRICT'), nullable = False)

    
    user = db.relationship('User', backref = 'orders')
    items = db.relationship('Cart_Item', secondary = order_cart_items, backref = 'orders')
    address = db.relationship('Address', backref = 'orders', foreign_keys=[shipping_address_id])

    def __init__ (self, user_id, date, total_price, status, stripe_payment_id, shipping_method, payment_status, shipping_address_id) :
        self.user_id = user_id
        self.date = date
        self.total_price = total_price
        self.status = status
        self.stripe_payment_id = stripe_payment_id
        self.shipping_method = shipping_method
        self.payment_status = payment_status
        self.shipping_address_id = shipping_address_id

    def as_dict (self) :
        return {
            'id': self.id,
            'totalPrice': self.total_price,
            'date': self.date.strftime('%m/%d/%Y %I:%M %p'),
            'status': serialize_enum(self.status),
            'shippingMethod': serialize_enum(self.shipping_method), 
            'paymentStatus': serialize_enum(self.payment_status),
            'address': self.address.as_dict(),
        }