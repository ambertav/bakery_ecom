"""empty message

Revision ID: 118ec14183e2
Revises: befc73f0a0cc
Create Date: 2024-08-31 00:09:20.657240

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '118ec14183e2'
down_revision = 'befc73f0a0cc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password',
               existing_type=sa.VARCHAR(length=128),
               type_=sa.LargeBinary(),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password',
               existing_type=sa.LargeBinary(),
               type_=sa.VARCHAR(length=128),
               existing_nullable=False)

    # ### end Alembic commands ###
