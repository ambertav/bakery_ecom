"""removes address fields from user model to create address model

Revision ID: 449e7b65fb75
Revises: 741929bfed9a
Create Date: 2023-10-22 02:14:37.840295

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '449e7b65fb75'
down_revision = '741929bfed9a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('addresses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('first_name', sa.String(length=50), nullable=False),
    sa.Column('last_name', sa.String(length=50), nullable=False),
    sa.Column('street', sa.String(length=255), nullable=False),
    sa.Column('city', sa.String(length=100), nullable=False),
    sa.Column('state', sa.String(length=2), nullable=False),
    sa.Column('zip_code', sa.String(length=10), nullable=False),
    sa.Column('type', sa.Enum('BILLING', 'SHIPPING', 'BOTH', name='addresstype'), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('billing_address')
        batch_op.drop_column('shipping_address')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('shipping_address', sa.TEXT(), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('billing_address', sa.TEXT(), autoincrement=False, nullable=True))

    op.drop_table('addresses')
    # ### end Alembic commands ###
