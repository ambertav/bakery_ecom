from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, TIMESTAMP, ForeignKey, CheckConstraint, and_, or_
from sqlalchemy.orm import validates
from sqlalchemy.exc import SQLAlchemyError
from enum import Enum
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_CEILING
import bcrypt

from ...database import db


def serialize_enum (enum_value) :
    return enum_value.value.lower()

# enum for portions
class Portion_Size (Enum) :
    SLICE = 'SLICE'
    WHOLE = 'WHOLE'
    MINI = 'MINI'

class Portion (db.Model) :
    __tablename__ = 'portions'

    id = db.Column(db.Integer, primary_key = True)
    product_id = db.Column(db.Integer, ForeignKey('products.id'), nullable = False)
    size = db.Column(db.Enum(Portion_Size), nullable = False)
    stock = db.Column(db.Integer, nullable = False)
    price = db.Column(db.Numeric(precision = 5, scale = 2), nullable = False)

    __table_args__ = (
        CheckConstraint('stock >= 0', name = 'non_negative_stock'),
        CheckConstraint('price >= 0', name = 'non_negative_price'),
    )

    product = db.relationship('Product', back_populates = 'portions')

    def __init__ (self, product_id, size, stock, price) :
        self.product_id = product_id
        self.size = size
        self.stock = stock

        self._calculate_price(price)

    def _calculate_price (self, price) :
        size_multipliers = {
            Portion_Size.WHOLE: Decimal('1'),
            Portion_Size.MINI: Decimal('0.5'),
            Portion_Size.SLICE: Decimal('0.15')
        }

        multiplier = size_multipliers.get(self.size, Decimal('1'))

        # price per portion
            # multiple product price by multiplier and round down
                # encourages last digit being 9, i.e 19.99 * .5 would round down to 9.99 rather than 10
        self.price = Decimal(Decimal(price) * multiplier).quantize(Decimal('0.00'), rounding = ROUND_DOWN)

    def as_dict (self) :
        return {
            'id': self.id,
            'size': serialize_enum(self.size),
            'stock': self.stock,
            'price': float(self.price)
        }


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

    __table_args__ = (
        CheckConstraint("image ~* '^https?://.*\.(png|jpg|jpeg|gif)$'", name = 'valid_image_url'),
    )

    portions = db.relationship('Portion', back_populates = 'product', cascade = 'all, delete-orphan')

    def __init__ (self, name, description, category, image) :
        self.name = name
        self.description = description
        self.category = Category(category)
        self.image = image or 'https://example.com/default_image.jpg'

    def create_portions (self, price) :
        portions = [Portion_Size.WHOLE]

        if self.category in [Category.CAKE, Category.PIE] :
            portions.extend([Portion_Size.MINI, Portion_Size.SLICE])
        elif self.category in [Category.CUPCAKE, Category.DONUT] :
            portions.append(Portion_Size.MINI)
        
        return [ Portion(product_id = self.id, size = size, stock = 0, price = price) for size in portions ]


    def update_attributes (self, data) :
        for key, value in data.items() :
            if hasattr(self, key) and getattr(self, key) != value :
                setattr(self, key, value)
    
    
    def as_dict (self) : 
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': serialize_enum(self.category),
            'image': self.image,
            'portions': [ portion.as_dict() for portion in self.portions ]
        }


# User
class User (db.Model) :
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(30), nullable = False)
    firebase_uid = db.Column(db.String(128), nullable = False)
    created_at = db.Column(db.TIMESTAMP(), nullable = False)

    addresses = db.relationship('Address', backref = 'user', lazy = 'dynamic')

    def __init__ (self, name, firebase_uid, created_at) :
        self.name = name
        self.firebase_uid = firebase_uid
        self.created_at = created_at


# Admin
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

    def toggle_default (self) :
        self.default = not self.default

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
    portion_id = db.Column(db.Integer, ForeignKey('portions.id'), nullable = False)
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
            name = 'cart_item_order_association_check'
        ),
    )

    # define relationships
    user = db.relationship('User', backref = 'cart_items')
    product = db.relationship('Product', backref = 'cart_items')
    portion = db.relationship('Portion')

    def __init__ (self, user_id, product_id, portion_id, quantity, ordered, order_id) :
        self.product, self.portion = self._validate_product_and_portion(product_id, portion_id)

        self.user_id = user_id
        self.product_id = product_id
        self.portion_id = portion_id
        self.quantity = quantity
        self.ordered = ordered
        self.order_id = order_id

        self._calculate_price()
    

    def _validate_product_and_portion (self, product_id, portion_id) :
        product = Product.query.filter_by(id = product_id).first()
        if product is None :
            raise ValueError('Product does not exist')
        
        portion = Portion.query.filter_by(id = portion_id).first()
        if portion is None :
            raise ValueError('Portion does not exist')
        
        if portion.product_id != product_id :
            raise ValueError('The portion does not correspond to selected product')
    
        return product, portion
    
    # calculating price of item based on quantity and portion
    def _calculate_price (self) :
        total_price = Decimal(self.portion.price) * Decimal(self.quantity)
        self.price = total_price.quantize(Decimal('0.01'), rounding = ROUND_CEILING)
    

    def update_quantity (self, new_quantity) :
        if new_quantity < 0 or new_quantity == None :
            raise ValueError('Invalid quantity provided')
        elif new_quantity == 0 :
            return 'delete'
        else :
            self.quantity = new_quantity
            self._calculate_price()
            

    def as_dict (self) :
        return {
            'id': self.id,
            'product': {
                'id': self.product.id,
                'name': self.product.name,
                'image': self.product.image
            },
            'price': float(self.price),
            'portion': {
                'id': self.portion.id,
                'size': serialize_enum(self.portion.size),
                'price': float(self.portion.price)
            },
            'quantity': self.quantity,
            'orderId': self.order_id
        }
    

# enums for order model
class Order_Status (Enum) :
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
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
    stripe_session_id = db.Column(db.String, nullable = True)
    stripe_payment_id = db.Column(db.String, nullable = True)
    delivery_method = db.Column(db.Enum(Deliver_Method), nullable = False)
    payment_status = db.Column(db.Enum(Pay_Status), nullable = False)
    shipping_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id', ondelete = 'RESTRICT'), nullable = False)

    
    user = db.relationship('User', backref = 'orders')
    cart_items = db.relationship('Cart_Item', backref = 'orders')
    address = db.relationship('Address', backref = 'orders', foreign_keys = [shipping_address_id])

    # one to one relationship, cascade deletion
    task = db.relationship('Task', backref = 'order', uselist = False, lazy = 'joined', cascade = 'all, delete-orphan')

    def __init__ (self, user_id, date, total_price, status, stripe_payment_id, delivery_method, payment_status, shipping_address_id) :
        self.user_id = user_id
        self.date = date
        self.total_price = total_price
        self.status = status
        self.stripe_payment_id = stripe_payment_id
        self.delivery_method = delivery_method
        self.payment_status = payment_status
        self.shipping_address_id = shipping_address_id


    def associate_items (self, cart_items) :
        for item in cart_items :
            item.order_id = self.id
            item.ordered = True
            self.cart_items.append(item)

    # method to create basic task associated to order instance
    def create_associated_task (self) :
        try :
            task = Task(
                admin_id = None,
                order_id = self.id,
                assigned_at = None,
                completed_at = None,
            )
            db.session.add(task)
            db.session.commit()

            return task
        
        except SQLAlchemyError as error :
            db.session.rollback()
            raise error
        
    def finalize_order_payment (self, session_id, payment_id) :
        self.stripe_session_id = session_id
        self.stripe_payment_id = payment_id
        self.payment_status =  Pay_Status.COMPLETED

    def status_start (self, admin_id) :
        self.status = Order_Status.IN_PROGRESS
        self.task.assign_admin(admin_id)

    def status_undo (self, admin_id) :
        self._validate_status_update(admin_id)
        self.status = Order_Status.PENDING
        self.task.unassign_admin()

    def status_complete (self, admin_id) :
        self._validate_status_update(admin_id)
        self.status = Order_Status.COMPLETED
        self.task.complete()

    def _validate_status_update (self, admin_id) :
        if self.status != Order_Status.IN_PROGRESS :
            raise ValueError('Order status could not be updated')
        if self.task.admin_id != admin_id:
            raise PermissionError('Requesting admin does not match assigned admin')

    def as_dict (self) :
        return {
            'id': self.id,
            'totalPrice': self.total_price,
            'date': self.date.strftime('%m/%d/%Y %I:%M %p'),
            'cartItems': [ item.as_dict() for item in self.cart_items ],
            'status': serialize_enum(self.status),
            'deliveryMethod': serialize_enum(self.delivery_method), 
            'paymentStatus': serialize_enum(self.payment_status),
            'address': self.address.as_dict(),
        }

class Task (db.Model) :
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key = True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable = True) 
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable = False)
    assigned_at = db.Column(db.TIMESTAMP(), nullable = True)
    completed_at = db.Column(db.TIMESTAMP(), nullable = True)

    def __init__ (self, admin_id, order_id, assigned_at, completed_at) :
        self.admin_id = admin_id
        self.order_id = order_id
        self.assigned_at = assigned_at
        self.completed_at = completed_at

    # assigns an admin if an admin is not already assigned
    def assign_admin (self, admin_id) :
        if self.admin_id or self.assigned_at is not None :
            return False
        else :
            self.admin_id = admin_id
            self.assigned_at = datetime.now(timezone.utc)
            return True

    # unassigns an admin if task is not already completed
    def unassign_admin (self) :
        if self.completed_at is not None :
            return False
        else :
            self.admin_id = None
            self.assigned_at = None
            return True

    # completes task as long as an admin is assigned
    def complete (self) :
        if self.admin_id is not None and self.assigned_at is not None :
            self.completed_at = datetime.now(timezone.utc)
            return True
        else :
            return False

    def as_dict (self) :
        admin = Admin.query.get(self.admin_id)
        admin_name = admin.name if admin else None
    
        return {
            'id': self.id,
            'adminName': admin_name,
            'orderId': self.order_id,
            'assignedAt': None if self.assigned_at is None else self.assigned_at.strftime('%m/%d/%Y %I:%M %p'),
            'completedAt': None if self.completed_at is None else self.completed_at.strftime('%m/%d/%Y %I:%M %p')
        }
