"""replaces type field with default

Revision ID: 69543763636e
Revises: 8dce2061d2c3
Create Date: 2023-10-31 00:32:52.204715

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '69543763636e'
down_revision = '8dce2061d2c3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('addresses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default', sa.Boolean(), nullable=False))
        batch_op.drop_column('type')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('addresses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('type', postgresql.ENUM('BILLING', 'SHIPPING', 'BOTH', name='addresstype'), autoincrement=False, nullable=False))
        batch_op.drop_column('default')

    # ### end Alembic commands ###
