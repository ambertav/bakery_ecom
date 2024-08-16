from enum import Enum
from sqlalchemy import CheckConstraint
from decimal import Decimal, ROUND_DOWN

from ...database import db

# enum for portions
class Portion_Size (Enum) :
    SLICE = 'SLICE'
    WHOLE = 'WHOLE'
    MINI = 'MINI'

class Portion (db.Model) :
    __tablename__ = 'portions'

    id = db.Column(db.Integer, primary_key = True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable = False)
    size = db.Column(db.Enum(Portion_Size), nullable = False)
    optimal_stock = db.Column(db.Integer, default = 10, nullable = False)
    stock = db.Column(db.Integer, nullable = False)
    price = db.Column(db.Numeric(precision = 5, scale = 2), nullable = False)

    __table_args__ = (
        CheckConstraint('stock >= 0', name = 'non_negative_stock'),
        CheckConstraint('price >= 0', name = 'non_negative_price'),
    )

    product = db.relationship('Product', back_populates = 'portions')

    def __init__ (self, product_id, size, stock, price, optimal_stock = 10) :
        self.product_id = product_id
        self.size = size
        self.stock = stock
        self.optimal_stock = optimal_stock

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

    def update_stock (self, new_stock) :
        self.stock = new_stock

    def as_dict (self) :
        return {
            'id': self.id,
            'size': self.size.value.lower(),
            'optimalStock': self.optimal_stock,
            'stock': self.stock,
            'price': float(self.price),
            'soldOut': True if self.stock == 0 else False
        }