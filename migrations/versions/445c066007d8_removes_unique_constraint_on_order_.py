"""removes unique constraint on order address

Revision ID: 445c066007d8
Revises: 69543763636e
Create Date: 2023-10-31 20:50:25.010847

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '445c066007d8'
down_revision = '69543763636e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_constraint('orders_shipping_address_id_key', type_='unique')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.create_unique_constraint('orders_shipping_address_id_key', ['shipping_address_id'])

    # ### end Alembic commands ###