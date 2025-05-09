"""generate config table

Revision ID: 5c420ac678c6
Revises: 0faf08436318
Create Date: 2025-04-16 06:11:33.283205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '5c420ac678c6'
down_revision: Union[str, None] = '0faf08436318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('workflow_mappings', 'sprint_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.create_foreign_key(None, 'workflow_mappings', 'jira_projects', ['project_key'], ['key'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'workflow_mappings', type_='foreignkey')
    op.alter_column('workflow_mappings', 'sprint_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###
