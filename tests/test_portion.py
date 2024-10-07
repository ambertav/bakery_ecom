
import pytest

from sqlalchemy.exc import IntegrityError
from decimal import Decimal, ROUND_DOWN

from ..database import db
from ..api.models import Product, Category, Portion, Portion_Size


@pytest.fixture(scope = 'module')
def seed_database () :
    try:
        cake = Product(
            name = 'Product 1',
            description = 'Should result in 3 portions with sizes whole, mini, and slice',
            category = Category.CAKE
        )

        cupcake = Product(
            name = 'Product 2',
            description = 'Should result in 2 portions with sizes whole and mini',
            category = Category.CUPCAKE
        )

        db.session.add_all([ cake, cupcake ])
        db.session.flush()

        yield cake, cupcake

    finally:
        db.session.rollback()
        db.session.close()


def test_create_portions (seed_database) :
    cake, cupcake = seed_database

    products = [
        {
            'product': cake,
            'expected_portions': 3,
            'price': 19.99
        },
        {
            'product': cupcake,
            'expected_portions': 2,
            'price': 4.99
        }
    ]

    for info in products :
        portions = info['product'].create_portions(price = info['price'])
        assert len(portions) == info['expected_portions']
        db.session.add_all(portions)
        db.session.commit()

        for portion in portions :
            assert portion.product == info['product']


@pytest.mark.parametrize('valid_price', [True, False])
def test_calculate_price (seed_database, valid_price) :
    cake, cupcake = seed_database

    size_multipliers = {
        Portion_Size.WHOLE: Decimal('1'),
        Portion_Size.MINI: Decimal('0.5'),
        Portion_Size.SLICE: Decimal('0.15')
    }

    new_price = Decimal('29.99') if valid_price else Decimal('-9.99')

    if valid_price :
        cake.update_attributes({ 'price': new_price })
        db.session.commit()

        portions = Portion.query.filter_by(product_id = cake.id)

        for portion in portions :
            assert portion.price == Decimal(size_multipliers[portion.size] * new_price).quantize(Decimal('0.00'), rounding = ROUND_DOWN)
        
    else :
        # testing column constraints by asserting presence of IntegrityError
        with pytest.raises(IntegrityError) as error :
            cake.update_attributes({ 'price': new_price })
            db.session.commit()

        db.session.rollback()
        assert error.type is IntegrityError


@pytest.mark.parametrize('valid_stock', [True, False])
def test_update_stock (seed_database, valid_stock) :
    cake, cupcake = seed_database

    portion = Portion.query.filter_by(product_id = cake.id, size = Portion_Size.WHOLE).first()

    new_stock = 100 if valid_stock else -10

    if valid_stock :
        portion.update_stock(new_stock)
        db.session.commit()

        assert portion.stock == new_stock
        
    else :
        # testing column constraints by asserting presence of IntegrityError
        with pytest.raises(IntegrityError) as error :
            portion.update_stock(new_stock)
            db.session.commit()

        db.session.rollback()
        assert error.type is IntegrityError