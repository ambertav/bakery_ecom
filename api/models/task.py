from datetime import datetime, timezone
from .admin import Admin

from ...database import db

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
