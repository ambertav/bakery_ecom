from .app import db
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, Numeric, TIMESTAMP, ForeignKey
from enum import Enum

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
    CLIENT = 1
    ADMIN = 2

# User
class User (db.Model) :
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(30), nullable = False)
    email = db.Column(db.String(320), unique = True, nullable = False)
    password = db.Column(db.String(100), nullable = False)
    billing_address = db.Column(db.Text(), nullable = False)
    shipping_address = db.Column(db.Text(), nullable = True) # nullable for shipping same as billing option
    role = db.Column(db.Enum(Role), default = 1, nullable = False)
    created_at = db.Column(db.TIMESTAMP(), nullable = False)

    def __init__ (self, name, email, password, billing_address, shipping_address, role, created_at) :
        self.name = name
        self.email = email
        self.password = password
        self.billing_address = billing_address
        self.shipping_address = shipping_address
        self.role = role
        self.created_at = created_at


# Cart_item
class Cart_Item (db.Model) :
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable = False)
    product_id = db.Column(db.Integer, ForeignKey('products.id'), nullable = False)
    quantity = db.Column(db.Integer(), nullable = False)

    # define relationships
    user = db.relationship('User', backref = 'cart_items')
    product = db.relationship('Product', backref = 'cart_items')

    def __init__ (self, user_id, product_id, quantity) :
        self.user_id = user_id
        self.product_id = product_id
        self.quantity = quantity

    def as_dict (self) :
        return {
            'id': self.id,
            'product_id': self.product.id,
            'name': self.product.name,
            'image': self.product.image,
            'price': self.product.price,
            'quantity': self.quantity
        }
    
# enums for order model
class Order_Status (Enum) :
    PENDING = 1
    PROCESSING = 2
    SHIPPED = 3
    DELIVERED = 4
    CANCELLED = 5

class Ship_Method (Enum) :
    STANDARD = 1
    EXPRESS = 2
    NEXT_DAY = 3

class Pay_Method (Enum) :
    CREDIT_CARD = 1
    PAYPAL = 2
    CASH = 3

class Pay_Status (Enum) :
    PENDING = 1
    COMPLETED = 2
    FAILED = 3

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
    status = db.Column(db.Enum(Order_Status), default = 1, nullable = False)
    shipping_method = db.Column(db.Enum(Ship_Method), nullable = False)
    payment_method = db.Column(db.Enum(Pay_Method), nullable = False)
    payment_status = db.Column(db.Enum(Pay_Status), default = 1, nullable = False)
    
    user = db.relationship('User', backref = 'orders')
    items = db.relationship('Cart_Item', secondary = order_cart_items, backref = 'orders')

    def __init__ (self, user_id, date, status, shipping_method, payment_method, payment_status) :
        self.user_id = user_id
        self.date = date
        self.status = status
        self.shipping_method = shipping_method
        self.payment_method = payment_method
        self.payment_status = payment_status

    def total_price (self) :
        return sum(cart_item.product.price * cart_item.quantity for cart_item in self.items)