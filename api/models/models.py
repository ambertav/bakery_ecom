from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, TIMESTAMP, ForeignKey, CheckConstraint, and_, or_
from sqlalchemy.orm import validates
from enum import Enum

from ...database import db


def serialize_enum (enum_value) :
    return enum_value.value.lower()


# enum for product category
class Category (Enum) :
    CAKE = 'CAKE'
    CUPCAKE = 'CUPCAKE'
    PIE = 'PIE'
    COOKIE = 'COOKIE'
    DONUT = 'DONUT'
    PASTRY = 'PASTRY'

# Product
class Product (db.Model) :
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(80), nullable = False)
    description = db.Column(db.String(500), nullable = False)
    category = db.Column(db.Enum(Category), nullable = False)
    image = db.Column(db.String(), nullable = False, default = 'https://example.com/default_image.jpg')
    price = db.Column(db.Numeric(precision = 5, scale = 2), nullable = False)
    stock = db.Column(db.Integer(), nullable = False)

    __table_args__ = (
        CheckConstraint('stock >= 0', name = 'non_negative_stock'),
        CheckConstraint('price >= 0', name = 'non_negative_price'),
        CheckConstraint("image ~* '^https?://.*\.(png|jpg|jpeg|gif)$'", name = 'valid_image_url'),
    )

    def __init__ (self, name, description, category, image, price, stock) :
        self.name = name
        self.description = description
        self.category = category
        self.image = image or 'https://example.com/default_image.jpg'
        self.price = price
        self.stock = stock
    
    def as_dict (self) : 
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': serialize_enum(self.category),
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
    zip = db.Column(db.String(5), nullable = False)
    default = db.Column(db.Boolean, nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)

    __table_args__ = (
        CheckConstraint("LENGTH(zip) = 5 AND zip ~ '^[0-9]{5}$'", name = 'zip_format_constraint'),
    )

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


# enum for cart item portions
class Portion (Enum) :
    SLICE = 'SLICE'
    WHOLE = 'WHOLE'
    MINI = 'MINI'

# Cart_item
class Cart_Item (db.Model) :
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable = False)
    product_id = db.Column(db.Integer, ForeignKey('products.id'), nullable = False)
    portion = db.Column(db.Enum(Portion), nullable = False)
    quantity = db.Column(db.Integer(), nullable = False)
    price = db.Column(db.Numeric(precision = 5, scale = 2), nullable = False)
    ordered = db.Column(db.Boolean(), default = False, nullable = False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable = True)

    __table_args__ = (
        CheckConstraint('quantity >= 1', name = 'non_negative_quantity'),
         CheckConstraint(
            or_(
                and_(ordered == True, order_id != None),
                and_(ordered == False, order_id == None)
            ),
            name='cart_item_order_association_check'
        ),
    )

    # ensuring that only valid portions are selected based on product's category
    @validates('portion')
    def validate_portion (self, key, portion) :
        product = Product.query.get(self.product_id)

        if product.category in [Category.PASTRY, Category.COOKIE] :
            if portion is not Portion.WHOLE :
                raise ValueError('Only the whole portion is available for pastries and cookies')
        elif product.category in [Category.CUPCAKE, Category.DONUT] :
            if portion not in [Portion.WHOLE, Portion.MINI] :
                raise ValueError('Only the whole and mini portions are available for cupcakes and donuts')
        elif product.category in [Category.CAKE, Category.PIE] :
            if portion not in [Portion.SLICE, Portion.WHOLE, Portion.MINI] :
                raise ValueError('Invalid portion selection')
        return portion


    # define relationships
    user = db.relationship('User', backref = 'cart_items')
    product = db.relationship('Product', backref = 'cart_items')

    def __init__ (self, user_id, product_id, portion, quantity, ordered, order_id) :
        self.user_id = user_id
        self.product_id = product_id
        self.portion = portion
        self.quantity = quantity
        self.ordered = ordered
        self.order_id = order_id

        self.product = Product.query.filter_by(id=product_id).first()
        if self.product is None :
            raise ValueError(f'Product does not exist')
        
        self.calculate_price()

    # calculating price of item based on quantity and portion
    def calculate_price (self) :
        if self.portion == Portion.WHOLE :
            portion_multipler = 1
        elif self.portion == Portion.MINI :
            portion_multipler = 0.5
        elif self.portion == Portion.SLICE :
            portion_multipler = 0.15
        
        self.price = round((self.product.price * self.quantity * portion_multipler), 2)

    def as_dict (self) :
        return {
            'id': self.id,
            'productId': self.product.id,
            'name': self.product.name,
            'image': self.product.image,
            'price': self.price,
            'portion': serialize_enum(self.portion),
            'quantity': self.quantity,
            'orderId': self.order_id
        }
    

# enums for order model
class Order_Status (Enum) :
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    DELIVERED = 'DELIVERED'
    CANCELLED = 'CANCELLED'

class Deliver_Method (Enum) :
    STANDARD = 'STANDARD'
    EXPRESS = 'EXPRESS'
    NEXT_DAY = 'NEXT_DAY'
    PICK_UP = 'PICK_UP'

class Pay_Status (Enum) :
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

# Order
class Order (db.Model) :
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable = False)
    total_price = db.Column(db.Numeric(precision = 10, scale = 2), nullable = False)
    date = db.Column(db.TIMESTAMP(), nullable = False)
    status = db.Column(db.Enum(Order_Status), nullable = False)
    stripe_payment_id = db.Column(db.String, nullable = True)
    delivery_method = db.Column(db.Enum(Deliver_Method), nullable = False)
    payment_status = db.Column(db.Enum(Pay_Status), nullable = False)
    shipping_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id', ondelete = 'RESTRICT'), nullable = False)

    
    user = db.relationship('User', backref = 'orders')
    cart_items = db.relationship('Cart_Item', backref = 'orders')
    address = db.relationship('Address', backref = 'orders', foreign_keys = [shipping_address_id])

    def __init__ (self, user_id, date, total_price, status, stripe_payment_id, delivery_method, payment_status, shipping_address_id) :
        self.user_id = user_id
        self.date = date
        self.total_price = total_price
        self.status = status
        self.stripe_payment_id = stripe_payment_id
        self.delivery_method = delivery_method
        self.payment_status = payment_status
        self.shipping_address_id = shipping_address_id

    def as_dict (self) :
        return {
            'id': self.id,
            'totalPrice': self.total_price,
            'date': self.date.strftime('%m/%d/%Y %I:%M %p'),
            'status': serialize_enum(self.status),
            'deliveryMethod': serialize_enum(self.delivery_method), 
            'paymentStatus': serialize_enum(self.payment_status),
            'address': self.address.as_dict(),
        }