from sqlalchemy import CheckConstraint, and_, or_
from decimal import Decimal, ROUND_CEILING

from .product import Product
from .portion import Portion

from ...database import db


class Cart_Item (db.Model) :
    '''
    Represents an item in a user's shopping cart.

    Attributes :
        id (int) : unique identifier for cart item.
        user_id (int) : ID of the user who owns the cart item.
        product_id (int) : ID of the product associated with cart item.
        portion_id (int) : ID of the portion associated with cart item.
        quantity (int) : quantity of the product in the cart.
        price (Decimal) : price of the cart item (accounts for quantity).
        ordered (bool) : Whether the item has been ordered.
        order_id (int or None) : ID of the order if the item has been ordered.
        user (relationship) :  relationship to the user owning the cart item.
        product (relationship) : relationship to the product associated with the cart item.
        portion (relationship) : relationship to the portion associated with the cart item.
    '''
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
        # ensures quantity is equal or greater to 1
        CheckConstraint('quantity >= 1', name = 'non_negative_quantity'),

        # ensures that...
            # if ordered, order_id is not None
            # if not ordered, order_id is None
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

    def __init__ (self, user_id, product_id, portion_id, quantity) :
        '''
        Initializes a new cart_item instance.

        Args :
            user_id (int) : ID of the user who owns the cart item.
            product_id (int) : ID of the product associated with cart item.
            portion_id (int) : ID of the portion associated with cart item.
            quantity (int) : quantity of the product in the cart.
            ordered (bool) : Whether the item has been ordered.
            order_id (int or None) : ID of the order if the item has been ordered.
        '''
        # verifies product and portion and then defines relationship
        self.product, self.portion = self._validate_product_and_portion(product_id, portion_id)

        self.user_id = user_id
        self.product_id = product_id
        self.portion_id = portion_id
        self.quantity = quantity
        self.ordered = False
        self.order_id = None

        self._calculate_price()
    
    def _validate_product_and_portion (self, product_id, portion_id) :
        '''
        Validates the product and portion IDs prior to initializing cart_item.

        Args :
            product_id (int) : ID of the product.
            portion_id (int) : ID of the portion.

        Returns :
            tuple : tuple containing the Product and Portion instances.
        
        Raises :
            ValueError : if product or portion does not exist, or if the portion does not correspond to the product.
        '''
        product = Product.query.filter_by(id = product_id).first()

        if product is None :
            raise ValueError('Product does not exist')
        
        portion = Portion.query.filter_by(id = portion_id).first()
        if portion is None :
            raise ValueError('Portion does not exist')
        
        if portion.product_id != product_id :
            raise ValueError('The portion does not correspond to selected product')
    
        return product, portion
    
    def _calculate_price (self) :
        '''
        Calculates the price of the cart_item based on quantity and portion price.
        Updates the price attribute with the calculated value.
        '''
        total_price = Decimal(self.portion.price) * Decimal(self.quantity)
        self.price = total_price.quantize(Decimal('0.01'), rounding = ROUND_CEILING)
    

    def update_quantity (self, new_quantity) :
        '''
        Updates the quantity of the cart_item.

        Args :
            new_quantity (int) : new quantity for the cart_item.
        
        Returns :
            str : 'delete' if the new quantity is zero and cart_item should be deleted.
            None : if quantity and price were successfully updated.
        
        Raises :
            ValueError : if the new quantity is negative or None.
        '''
        if new_quantity < 0 or new_quantity == None :
            raise ValueError('Invalid quantity provided')
        elif new_quantity == 0 :
            return 'delete'
        else :
            self.quantity = new_quantity
            self._calculate_price()
            

    def as_dict (self) :
        '''
        Converts cart_item to a dictionary.

        Returns :
            dict : dictionary representation of the cart_item, including product and portion details. NOTE: camelCasing for ease in frontend.
        '''
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