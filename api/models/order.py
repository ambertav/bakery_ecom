from sqlalchemy.exc import SQLAlchemyError
from enum import Enum
from .task import Task

from ...database import db


class Order_Status (Enum) :
    '''
    Enum for representing status of order.

    Attributes :
        PENDING (str) : Order is pending.
        IN_PROGRESS (str) : Order is being processed.
        COMPLETED (str) : Order is completed.
        DELIVERED (str) : Order has been delivered.
        CANCELLED (str) : Order has been cancelled.
    '''

    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    DELIVERED = 'DELIVERED'
    CANCELLED = 'CANCELLED'

class Deliver_Method (Enum) :
    '''
    Enum for representing the delivery method of an order.

    Attributes :
        STANDARD (str) : Standard delivery method.
        EXPRESS (str) : Express delivery method.
        NEXT_DAY (str) : Next-day delivery method.
        PICK_UP (str) : Pick-up delivery method.
    '''

    STANDARD = 'STANDARD'
    EXPRESS = 'EXPRESS'
    NEXT_DAY = 'NEXT_DAY'
    PICK_UP = 'PICK_UP'

class Pay_Status (Enum) :
    '''
    Enum for representing the payment status of an order.

    Attributes :
        PENDING (str) : Payment is pending.
        COMPLETED (str) : Payment is completed.
        FAILED (str) : Payment has failed.
    '''

    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class Order (db.Model) :
    '''
    Represents an order in the system.

    Attributes:
        id (int) : unique identifier for the order.
        user_id (int) : ID of the user who placed the order.
        total_price (Decimal) : total price of the order.
        date (datetime) : date and time when the order was placed.
        status (Order_Status) : status of the order.
        stripe_session_id (str or None) : Stripe session ID for payment, if applicable.
        stripe_payment_id (str or None) : Stripe payment ID for payment, if applicable.
        delivery_method (Deliver_Method) : delivery method for the order.
        payment_status (Pay_Status) : payment status of the order.
        shipping_address_id (int) : ID of the shipping address.
        user (relationship) : relationship to the user who placed the order.
        cart_items (relationship) : relationship to the cart items associated with the order.
        address (relationship) : relationship to the shipping address.
        task (relationship) : relationship to the task associated with the order.
    '''
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

    # define relationships
    user = db.relationship('User', backref = 'orders')
    cart_items = db.relationship('Cart_Item', backref = 'orders')
    address = db.relationship('Address', backref = 'orders', foreign_keys = [shipping_address_id])

    # one to one relationship, cascade deletion
    task = db.relationship('Task', backref = 'order', uselist = False, lazy = 'joined', cascade = 'all, delete-orphan')

    def __init__ (self, user_id, date, total_price, status, delivery_method, payment_status, shipping_address_id) :
        '''
        Initializes a new order instance.

        Args :
            user_id (int) : ID of the user who placed the order.
            date (datetime) : date and time when the order was placed.
            total_price (Decimal) : total price of the order.
            status (Order_Status) : status of the order.
            delivery_method (Deliver_Method) : delivery method for the order.
            payment_status (Pay_Status) : payment status of the order.
            shipping_address_id (int) : ID of the shipping address.
        '''
        self.user_id = user_id
        self.date = date
        self.total_price = total_price
        self.status = status
        self.delivery_method = delivery_method
        self.payment_status = payment_status
        self.shipping_address_id = shipping_address_id


    def associate_items (self, cart_items) :
        '''
        Associates cart_items with order and marks them as ordered.

        Args :
            cart_items (list) : list of cart_item instances to be associated with the order.
        '''
        for item in cart_items :
            item.order_id = self.id
            item.ordered = True
            self.cart_items.append(item)

    def create_associated_task (self) :
        '''
        Creates a new task associated with the order.

        Returns :
            Task : newly created task instance.
        
        Raises :
            SQLAlchemyError : if there is an error during task creation.
        '''
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
        '''
        Finalizes order payment by setting Stripe session, setting Stripe payment ID, and updating payment status.

        Args :
            session_id (str) : Stripe session ID.
            payment_id (str) : Stripe payment ID.
        '''
        self.stripe_session_id = session_id
        self.stripe_payment_id = payment_id
        self.payment_status =  Pay_Status.COMPLETED

    def status_start (self, admin_id) :
        '''
        Marks the order as in progress and assigns the task to the admin.

        Args :
            admin_id (int) : ID of the admins to assign to the task.
        '''
        self.status = Order_Status.IN_PROGRESS
        self.task.assign_admin(admin_id)

    def status_undo (self, admin_id) :
        '''
        Reverts order status to pending and unassigns the admin from the task.

        Args :
            admin_id (int) : ID of the admin to unassign.
        
        Raises :
            ValueError : if the order status is not in progress.
            PermissionError : if the requesting admin does not match the assigned admin.
        '''
        self._validate_status_update(admin_id)
        self.status = Order_Status.PENDING
        self.task.unassign_admin()

    def status_complete (self, admin_id) :
        '''
        Marks order as completed and updates the task status.

        Args :
            admin_id (int) : ID of the admin who completed the order.
        
        Raises :
            ValueError : if the order status is not in progress.
            PermissionError : if the requesting admin does not match the assigned admin.
        '''
        self._validate_status_update(admin_id)
        self.status = Order_Status.COMPLETED
        self.task.complete()

    def _validate_status_update (self, admin_id) :
        '''
        Validates if the status update is allowed based on current order status and admin assignment.

        Args:
            admin_id (int) : ID of the requesting admin.

        Raises:
            ValueError : if the order status is not in progress.
            PermissionError : if the requesting admin does not match the assigned admin.
        '''
        if self.status != Order_Status.IN_PROGRESS :
            raise ValueError('Order status could not be updated')
        if self.task.admin_id != admin_id:
            raise PermissionError('Requesting admin does not match assigned admin')

    def as_dict (self) :
        '''
        Converts order to a dictionary.

        Returns :
            dict : dictionary representation of the order, including associated cart_items and address. NOTE: camelCasing for ease in frontend.
        '''
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
