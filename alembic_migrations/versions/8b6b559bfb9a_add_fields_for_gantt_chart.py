"""add fields for gantt chart

Revision ID: 8b6b559bfb9a
Revises: a15642f30e06
Create Date: 2025-05-01 17:34:07.165887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '8b6b559bfb9a'
down_revision: Union[str, None] = 'a15642f30e06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('jira_issues', sa.Column('planned_start_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jira_issues', sa.Column('planned_end_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jira_issues', sa.Column('actual_start_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jira_issues', sa.Column('actual_end_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jira_issues', sa.Column('story_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_foreign_key(None, 'jira_issues', 'jira_issues', ['story_id'], ['jira_issue_id'])
    # op.drop_index('ix_system_configs_project_key', table_name='system_configs')
    # op.drop_constraint('uq_system_configs_key_scope_project', 'system_configs', type_='unique')
    # op.create_unique_constraint('uq_system_configs_key_scope', 'system_configs', ['key', 'scope'])
    # op.drop_column('system_configs', 'project_key')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('system_configs', sa.Column('project_key', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_constraint('uq_system_configs_key_scope', 'system_configs', type_='unique')
    op.create_unique_constraint('uq_system_configs_key_scope_project',
                                'system_configs', ['key', 'scope', 'project_key'])
    op.create_index('ix_system_configs_project_key', 'system_configs', ['project_key'], unique=False)
    op.create_index('ix_system_configs_id', 'system_configs', ['id'], unique=False)
    op.drop_constraint(None, 'jira_issues', type_='foreignkey')
    op.drop_column('jira_issues', 'story_id')
    op.drop_column('jira_issues', 'actual_end_time')
    op.drop_column('jira_issues', 'actual_start_time')
    op.drop_column('jira_issues', 'planned_end_time')
    op.drop_column('jira_issues', 'planned_start_time')
    # ### end Alembic commands ###
