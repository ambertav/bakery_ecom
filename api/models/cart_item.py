from sqlalchemy import CheckConstraint, and_, or_
from decimal import Decimal, ROUND_CEILING
from .product import Product
from .portion import Portion

from ...database import db

class Cart_Item (db.Model) :
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable = False)
    portion_id = db.Column(db.Integer, db.ForeignKey('portions.id'), nullable = False)
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
                'size': self.portion.size.value.lower(),
                'price': float(self.portion.price)
            },
            'quantity': self.quantity,
            'orderId': self.order_id
        }