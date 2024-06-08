"""Added cascade delete for ownerships

Revision ID: 7349a63fbf69
Revises: 0de90ea466a3
Create Date: 2024-06-06 21:42:37.968531

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7349a63fbf69'
down_revision: Union[str, None] = '0de90ea466a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('patent_reg_number_key', 'patent', type_='unique')
    op.create_index(op.f('ix_patent_reg_number'), 'patent', ['reg_number'], unique=True)
    op.create_index(op.f('ix_person_tax_number'), 'person', ['tax_number'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_person_tax_number'), table_name='person')
    op.drop_index(op.f('ix_patent_reg_number'), table_name='patent')
    op.create_unique_constraint('patent_reg_number_key', 'patent', ['reg_number'])
    # ### end Alembic commands ###