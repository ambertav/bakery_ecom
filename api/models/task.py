from datetime import datetime, timezone
from .admin import Admin

from ...database import db

class Task (db.Model) :
    '''
    Represents a task related to an order and assigned to an admin.

    Attributes :
        id (int) : unique identifier for the task.
        admin_id (int or None) : ID of the admin assigned to the task, if applicable.
        order_id (int) : ID of the associated order.
        assigned_at (datetime or None) : timestamp when the task was assigned, if applicable.
        completed_at (datetime or None) : timestamp when the task was completed, if applicable.
    '''
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key = True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable = True) 
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable = False)
    assigned_at = db.Column(db.TIMESTAMP(), nullable = True)
    completed_at = db.Column(db.TIMESTAMP(), nullable = True)

    def __init__ (self, admin_id, order_id, assigned_at, completed_at) :
        '''
        Initializes a new task instance.

        Args :
            admin_id (int or None) : ID of the admin assigned to the task, if applicable.
            order_id (int) : ID of the associated order.
            assigned_at (datetime or None) : timestamp when the task was assigned, if applicable.
            completed_at (datetime or None) : timestamp when the task was completed, if applicable.
        '''
        self.admin_id = admin_id
        self.order_id = order_id
        self.assigned_at = assigned_at
        self.completed_at = completed_at

    def assign_admin (self, admin_id) :
        '''
        Assigns an admin to the task if no admin is currently assigned to the task.

        Args :
            admin_id (int) : ID of the admin to assign.

        Returns :
            bool : True if admin was successfully assigned, False otherwise.
        '''
        if self.admin_id or self.assigned_at is not None :
            return False
        else :
            self.admin_id = admin_id
            self.assigned_at = datetime.now(timezone.utc)
            return True

    def unassign_admin (self) :
        '''
        Unassigned the admin from the task if the task is not already completed.

        Returns :
            bool : True if the admin was successfully unassigned, False otherwise.
        '''
        if self.completed_at is not None :
            return False
        else :
            self.admin_id = None
            self.assigned_at = None
            return True

    def complete (self) :
        '''
        Marks the task as completed if admin is assigned to the task.

        Returns :
            bool : True if the task was successfully marked as completed, False otherwise.
        '''
        if self.admin_id is not None and self.assigned_at is not None :
            self.completed_at = datetime.now(timezone.utc)
            return True
        else :
            return False

    def as_dict (self) :
        '''
        Converts the task to a dictionary.

        Returns :
            dict : dictionary representation of the task, including admin name, order ID. NOTE: camelCasing for ease in frontend.
        '''
        admin = Admin.query.get(self.admin_id)
        admin_name = admin.name if admin else None
    
        return {
            'id': self.id,
            'adminName': admin_name,
            'orderId': self.order_id,
            'assignedAt': None if self.assigned_at is None else self.assigned_at.strftime('%m/%d/%Y %I:%M %p'),
            'completedAt': None if self.completed_at is None else self.completed_at.strftime('%m/%d/%Y %I:%M %p')
        }
