"""Add unique constraint on hardware.serial_number

Revision ID: 0c3b1a6a1f2b
Revises: afb721449e21
Create Date: 2025-??
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '0c3b1a6a1f2b'
down_revision = 'afb721449e21'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint('uq_hardware_serial_number', 'hardware', ['serial_number'])


def downgrade():
    op.drop_constraint('uq_hardware_serial_number', 'hardware', type_='unique')
