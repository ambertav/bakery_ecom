from ...database import db

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