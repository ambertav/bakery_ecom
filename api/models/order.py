from sqlalchemy.exc import SQLAlchemyError
from enum import Enum
import importlib

from ...database import db


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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
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

    def _get_task_model (self) :
        models_module = importlib.import_module('app.models')
        return getattr(models_module, 'Task')

    # method to create basic task associated to order instance
    def create_associated_task (self) :
        Task = self._get_task_model()
        
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
            'status': self.status.value.lower(),
            'deliveryMethod': self.delivery_method.value.lower(),
            'paymentStatus': self.payment_status.value.lower(),
            'address': self.address.as_dict(),
        }
