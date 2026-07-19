"""Create the initial migration checkpoint.

No domain tables are defined in DATA-001. This revision establishes a stable
Alembic head so future model migrations have an explicit parent.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Establish the initial migration checkpoint."""


def downgrade() -> None:
    """Remove the initial checkpoint (Alembic handles the version row)."""
