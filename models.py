from .app import db
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, Numeric


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
