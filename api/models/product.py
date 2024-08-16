from enum import Enum
from sqlalchemy import CheckConstraint
from .portion import Portion, Portion_Size


from ...database import db

# enum for product category
class Category (Enum) :
    CAKE = 'CAKE'
    CUPCAKE = 'CUPCAKE'
    PIE = 'PIE'
    COOKIE = 'COOKIE'
    DONUT = 'DONUT'
    PASTRY = 'PASTRY'

# Product
class Product (db.Model) :
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(80), nullable = False)
    description = db.Column(db.String(500), nullable = False)
    category = db.Column(db.Enum(Category), nullable = False)
    image = db.Column(db.String(), nullable = False, default = 'https://example.com/default_image.jpg')

    __table_args__ = (
        CheckConstraint("image ~* '^https?://.*\.(png|jpg|jpeg|gif)$'", name = 'valid_image_url'),
    )

    portions = db.relationship('Portion', back_populates = 'product', cascade = 'all, delete-orphan')

    def __init__ (self, name, description, category, image) :
        self.name = name
        self.description = description
        self.category = Category(category)
        self.image = image or 'https://example.com/default_image.jpg'

    def create_portions (self, price) :
        portions = [Portion_Size.WHOLE]

        if self.category in [Category.CAKE, Category.PIE] :
            portions.extend([Portion_Size.MINI, Portion_Size.SLICE])
        elif self.category in [Category.CUPCAKE, Category.DONUT] :
            portions.append(Portion_Size.MINI)
        
        return [ Portion(product_id = self.id, size = size, stock = 0, price = price) for size in portions ]


    def update_attributes (self, data) :
        for key, value in data.items() :
            if hasattr(self, key) and getattr(self, key) != value :
                setattr(self, key, value)
    
    
    def as_dict (self) : 
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value.lower(),
            'image': self.image,
            'portions': [ portion.as_dict() for portion in self.portions ]
        }
