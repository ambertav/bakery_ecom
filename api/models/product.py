from enum import Enum
from sqlalchemy import CheckConstraint
from .portion import Portion, Portion_Size

from ...database import db


class Category (Enum) :
    '''
    Enum for representing product categories.

    Attributes :
        CAKE (str) : represents a cake product.
        CUPCAKE (str) : represents a cupcake product.
        PIE (str) : represents a pie product.
        COOKIE (str) : represents a cookie product.
        DONUT (str) : represents a donut product.
        PASTRY (str) : represents a pastry product.
    '''
    CAKE = 'CAKE'
    CUPCAKE = 'CUPCAKE'
    PIE = 'PIE'
    COOKIE = 'COOKIE'
    DONUT = 'DONUT'
    PASTRY = 'PASTRY'

# Product
class Product (db.Model) :
    '''
    Represents a product.

    Attributes :
        id (int) : unique identifier for the product.
        name (str) : name of the product.
        description (str) : description of the product.
        category (Category) : category of the product.
        image (str) : URL of the product image.
        portions (relationship) : relationship to portions associated with the product.
    '''
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(80), nullable = False)
    description = db.Column(db.String(500), nullable = False)
    category = db.Column(db.Enum(Category), nullable = False)
    image = db.Column(db.String(), nullable = False, default = 'https://example.com/default_image.jpg')

    __table_args__ = (
        # validation for image url string
        CheckConstraint("image ~* '^https?://.*\.(png|jpg|jpeg|gif)$'", name = 'valid_image_url'),
    )

    # defines relationship
    portions = db.relationship('Portion', back_populates = 'product', cascade = 'all, delete-orphan')

    def __init__ (self, name, description, category) :
        '''
        Initializes a new product instance.

        Args :
            name (str) : name of the product.
            description (str) : description of the product.
            category (Category) : category of the product.
            image (str) : URL of the product image.
        '''
        self.name = name
        self.description = description
        self.category = Category(category)
        self.image = 'https://example.com/default_image.jpg'

    def create_portions (self, price) :
        '''
        Creates portion for the product based on the product's category.

        Args :
            price (Decimal) : base price for each portion.
        
        Returns :
            list : list of Portion instances associated with the product.
        '''
        portions = [Portion_Size.WHOLE]

        if self.category in [Category.CAKE, Category.PIE] :
            portions.extend([Portion_Size.MINI, Portion_Size.SLICE])
        elif self.category in [Category.CUPCAKE, Category.DONUT] :
            portions.append(Portion_Size.MINI)
        
        return [ Portion(product_id = self.id, size = size, stock = 0, price = price) for size in portions ]


    def update_attributes (self, data) :
        '''
        Updates the product's attributes based on provided data.

        Args :
            data (dict) : dictionary where keys are product attribute names and values are new values for those attributes
        '''
        for key, value in data.items() :
            if hasattr(self, key) and getattr(self, key) != value :
                setattr(self, key, value)
    
    
    def as_dict (self) : 
        '''
        Converts the product to a dictionary.

        Returns :
            dict : dictionary representation of the product, including associated portions. NOTE: camelCasing for ease in frontend.
        '''
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value.lower(),
            'image': self.image,
            'portions': [ portion.as_dict() for portion in self.portions ]
        }
