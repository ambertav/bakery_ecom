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
    role = db.Column(db.Enum(Role), default = Role.CLIENT, nullable = False)
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

    def __init__ (self, user_id, product_id, quantity) :
        self.user_id = user_id
        self.product_id = product_id
        self.quantity = quantity