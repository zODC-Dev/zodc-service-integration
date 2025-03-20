"""add fk

Revision ID: 478e7c60f0c2
Revises: c410153a43bb
Create Date: 2025-03-20 04:01:39.900868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '478e7c60f0c2'
down_revision: Union[str, None] = 'c410153a43bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First drop any existing foreign key constraints
    op.drop_constraint(
        'jira_issues_assignee_id_fkey',
        'jira_issues',
        type_='foreignkey'
    )
    op.drop_constraint(
        'jira_issues_reporter_id_fkey',
        'jira_issues',
        type_='foreignkey'
    )

    # Then drop the unique constraint and create the index
    op.drop_constraint('uq_users_jira_account_id', 'users', type_='unique')
    op.create_index(op.f('ix_users_jira_account_id'), 'users', ['jira_account_id'], unique=True)

    # Finally recreate the foreign key constraints
    op.create_foreign_key(
        'jira_issues_assignee_id_fkey',
        'jira_issues', 'users',
        ['assignee_id'], ['jira_account_id']
    )
    op.create_foreign_key(
        'jira_issues_reporter_id_fkey',
        'jira_issues', 'users',
        ['reporter_id'], ['jira_account_id']
    )


def downgrade() -> None:
    # Drop foreign keys first
    op.drop_constraint(
        'jira_issues_assignee_id_fkey',
        'jira_issues',
        type_='foreignkey'
    )
    op.drop_constraint(
        'jira_issues_reporter_id_fkey',
        'jira_issues',
        type_='foreignkey'
    )

    # Then drop the index and recreate the unique constraint
    op.drop_index(op.f('ix_users_jira_account_id'), table_name='users')
    op.create_unique_constraint('uq_users_jira_account_id', 'users', ['jira_account_id'])

    # Finally recreate the foreign keys
    op.create_foreign_key(
        'jira_issues_assignee_id_fkey',
        'jira_issues', 'users',
        ['assignee_id'], ['jira_account_id']
    )
    op.create_foreign_key(
        'jira_issues_reporter_id_fkey',
        'jira_issues', 'users',
        ['reporter_id'], ['jira_account_id']
    )
