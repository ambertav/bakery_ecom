from enum import Enum
from sqlalchemy import CheckConstraint
from decimal import Decimal, ROUND_DOWN

from ...database import db


class Portion_Size (Enum) :
    '''
    Enum for representing different sizes of portions.

    Attributes :
        SLICE (str) : represents a slice portion.
        WHOLE (str) : represents a whole portion.
        MINI (str) : represents a mini portion.
    '''
    SLICE = 'SLICE'
    WHOLE = 'WHOLE'
    MINI = 'MINI'

class Portion (db.Model) :
    '''
    Represents a portion of a product.

    Attributes :
        id (int) : unique identifier for the portion.
        product_id (int) : ID of the product to which the portion belongs.
        size (Portion_Size) : size of the portion.
        optimal_stock (int) : optimal stock level for the portion.
        stock (int) : current stock level of the portion.
        price (Decimal) : price of the portion.
        product (relationship) : relationship to the product to which the portion belongs.
    '''
    __tablename__ = 'portions'

    id = db.Column(db.Integer, primary_key = True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable = False)
    size = db.Column(db.Enum(Portion_Size), nullable = False)
    optimal_stock = db.Column(db.Integer, default = 10, nullable = False)
    stock = db.Column(db.Integer, nullable = False)
    price = db.Column(db.Numeric(precision = 5, scale = 2), nullable = False)

    __table_args__ = (
        # ensures that stock and price as equal or greater than 0
        CheckConstraint('stock >= 0', name = 'non_negative_stock'),
        CheckConstraint('price >= 0', name = 'non_negative_price'),
    )

    # define relationship
    product = db.relationship('Product', back_populates = 'portions')

    def __init__ (self, product_id, size, stock, price, optimal_stock = 10) :
        '''
        Initializes a new portion instance.

        Args :
            product_id (int) : ID of the product to which the portion belongs.
            size (Portion_Size) : size of the portion.
            stock (int) : current stock level of the portion.
            price (Decimal) : price of the portion.
            optimal_stock (int) : optimal stock level for the portion.
        '''
        self.product_id = product_id
        self.size = size
        self.stock = stock
        self.optimal_stock = optimal_stock

        self._calculate_price(price)

    def _calculate_price (self, price) :
        '''
        Calculates and sets the price of the portion based on its size.

        Args:
            price (Decimal) : base price for the portion.
        
        The method uses a multiplier based on the portion size to adjust the price.
        The final price is rounded down to two decimal places to encourage pricing 
        with last digit being 9 (e.g., 19.99 instead of 20.00).
        '''
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
        '''
        Updates the stock level of the portion.

        Args :
            new_stock (int) : new stock level for the portion.
        '''
        self.stock = new_stock

    def as_dict (self) :
        '''
        Converts the portion to a dictionary.

        Returns :
            dict : dictionary representation of the portion, including attributes and soldOut status. NOTE: camelCasing for ease in frontend.
        '''
        return {
            'id': self.id,
            'size': self.size.value.lower(),
            'optimalStock': self.optimal_stock,
            'stock': self.stock,
            'price': float(self.price),
            'soldOut': True if self.stock == 0 else False
        }