"""Add professional preference fields and profile reevaluation metadata."""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0003_profile_preferences"
down_revision: Union[str, None] = "0002_domain_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("profiles", sa.Column("seniority", sa.String(40)))
    op.add_column("profiles", sa.Column("reevaluation_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("profiles", sa.Column("reevaluation_reason", sa.String(120)))
    op.add_column("profiles", sa.Column("reevaluation_metadata", sa.JSON(), nullable=False, server_default=sa.text("('{}')")))
    op.add_column("profiles", sa.Column("versioned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.add_column("profile_preferences", sa.Column("seniority", sa.String(40)))
    op.add_column("profile_preferences", sa.Column("preferred_languages", sa.JSON(), nullable=False, server_default=sa.text("('[]')")))
    op.add_column("profile_preferences", sa.Column("salary_max", sa.Float()))
    op.add_column("profile_preferences", sa.Column("salary_period", sa.String(20)))
    op.add_column("profile_preferences", sa.Column("employment_types", sa.JSON(), nullable=False, server_default=sa.text("('[]')")))
    op.add_column("profile_preferences", sa.Column("excluded_constraints", sa.JSON(), nullable=False, server_default=sa.text("('[]')")))

def downgrade() -> None:
    for table, column in (("profile_preferences", "excluded_constraints"), ("profile_preferences", "employment_types"), ("profile_preferences", "salary_period"), ("profile_preferences", "salary_max"), ("profile_preferences", "preferred_languages"), ("profile_preferences", "seniority"), ("profiles", "versioned_at"), ("profiles", "reevaluation_metadata"), ("profiles", "reevaluation_reason"), ("profiles", "reevaluation_required"), ("profiles", "seniority")):
        op.drop_column(table, column)
