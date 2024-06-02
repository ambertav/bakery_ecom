import pytest
from datetime import datetime, timezone

from ..database import db
from .conftest import generate_firebase_uid
from ..api.models.models import Order, Admin,  Order_Status, Deliver_Method, Pay_Status, User, Address, Cart_Item, Portion, Product, Category

@pytest.fixture(scope = 'module')
def seed_database (flask_app, create_client_user) :
    try:
        user, test_uid = create_client_user

        product = Product(
            name = 'Product 1',
            description = 'Description 1',
            category = Category.CAKE,
            image = 'https://example.com/image.jpg',
            price = 10.00,
            stock = 50
        )
        db.session.add(product)
        db.session.commit()

        address = Address(
            first_name = 'Jane',
            last_name = 'Doe',
            street = '123 Main St',
            city = 'Anytown',
            state = 'NY',
            zip = '10001',
            default = False,
            user_id = user.id,
        )
        db.session.add(address)
        db.session.commit()

        cart_item = Cart_Item(
            user_id = user.id,
            product_id = product.id,
            quantity = 1,
            portion = Portion.WHOLE,
            ordered = False,
            order_id = None
        )
        db.session.add(cart_item)
        db.session.commit()

        db.session.refresh(cart_item)
        db.session.refresh(address)

        order = Order(
            user_id = user.id,
            total_price = product.price,
            date = datetime.now(timezone.utc),
            status = Order_Status.PENDING,
            stripe_payment_id = None,
            delivery_method = Deliver_Method.STANDARD,
            payment_status = Pay_Status.PENDING,
            shipping_address_id = address.id
        )
        db.session.add(order)
        db.session.commit()

        task = order.create_associated_task()

        second_admin = Admin(
            pin = 12345,
            name = 'other admin',
            firebase_uid = generate_firebase_uid(),
            created_at = datetime.now(timezone.utc)
        )
        db.session.add(second_admin)
        db.session.commit()


        # returns order for use throughout module tests
        yield order, task, second_admin

    finally:
        db.session.rollback()
        db.session.close()


def test_assign_task (flask_app, create_admin_user, seed_database) :
    # create admin user, and destructure variables from seed
    admin, test_uid = create_admin_user
    order, task, second_admin = seed_database

    # assign task to first admin
        # assert success and that admin.is and assigned at were filled in
    assert task.assign_admin(admin) is True
    assert task.admin_id is admin.id and not None
    assert task.assigned_at is not None

    # attempt to assign same task to another admin
        # assert failure and that the value of admin.id did not change
    assert task.assign_admin(second_admin) is False
    assert task.admin_id is admin.id and not None

@pytest.mark.parametrize('is_complete', [True, False])
def test_unassign_task (flask_app, create_admin_user, seed_database, is_complete) :
    # create admin user, and destructure variables from seed
    admin, test_uid = create_admin_user
    order, task, second_admin = seed_database

    # asserting that cannot unassign an admin if task is complete
    if not is_complete :
        task.completed_at = datetime.now(timezone.utc)
        assert task.unassign_admin() is False
        db.session.rollback()
    # else can unassign
    else :
        assert task.unassign_admin() is True
        assert task.admin_id is None
        assert task.assigned_at is None
        db.session.rollback()


@pytest.mark.parametrize('is_assigned', [True, False])
def test_complete_task (flask_app, create_admin_user, seed_database, is_assigned) :
    # create admin user, and destructure variables from seed
    admin, test_uid = create_admin_user
    order, task, second_admin = seed_database

    # asserting that can complete task if an admin is assigned
    if is_assigned :
        task.assign_admin(admin)
        assert task.complete() is True
        assert task.completed_at is not None
        db.session.rollback()
    # else cannot complete task
    else :
        task.unassign_admin()
        assert task.complete() is False
        assert task.completed_at is None

    
