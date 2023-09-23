"""empty message

Revision ID: 65f617431163
Revises: 8dff3054654b
Create Date: 2023-09-18 18:44:10.642136

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '65f617431163'
down_revision = '8dff3054654b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.alter_column('status',
               existing_type=postgresql.ENUM('PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED', name='order_status'),
               type_=sa.Integer(),
               existing_nullable=False)
        batch_op.alter_column('shipping_method',
               existing_type=postgresql.ENUM('STANDARD', 'EXPRESS', 'NEXT_DAY', name='ship_method'),
               type_=sa.Integer(),
               existing_nullable=False)
        batch_op.alter_column('payment_method',
               existing_type=postgresql.ENUM('CREDIT_CARD', 'PAYPAL', 'CASH', name='pay_method'),
               type_=sa.Integer(),
               existing_nullable=False)
        batch_op.alter_column('payment_status',
               existing_type=postgresql.ENUM('PENDING', 'COMPLETED', 'FAILED', name='pay_status'),
               type_=sa.Integer(),
               existing_nullable=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=postgresql.ENUM('CLIENT', 'ADMIN', name='role'),
               type_=sa.Integer(),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.Integer(),
               type_=postgresql.ENUM('CLIENT', 'ADMIN', name='role'),
               existing_nullable=False)

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.alter_column('payment_status',
               existing_type=sa.Integer(),
               type_=postgresql.ENUM('PENDING', 'COMPLETED', 'FAILED', name='pay_status'),
               existing_nullable=False)
        batch_op.alter_column('payment_method',
               existing_type=sa.Integer(),
               type_=postgresql.ENUM('CREDIT_CARD', 'PAYPAL', 'CASH', name='pay_method'),
               existing_nullable=False)
        batch_op.alter_column('shipping_method',
               existing_type=sa.Integer(),
               type_=postgresql.ENUM('STANDARD', 'EXPRESS', 'NEXT_DAY', name='ship_method'),
               existing_nullable=False)
        batch_op.alter_column('status',
               existing_type=sa.Integer(),
               type_=postgresql.ENUM('PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED', name='order_status'),
               existing_nullable=False)

    # ### end Alembic commands ###