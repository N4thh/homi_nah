"""Add booking constraints and indexes

Revision ID: add_booking_constraints
Revises: 
Create Date: 2025-01-12 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_booking_constraints'
down_revision = None  # Update this to the latest revision
branch_labels = None
depends_on = None


def upgrade():
    """Add booking constraints and indexes"""
    
    # Add check constraints
    op.create_check_constraint(
        'check_booking_time_valid',
        'booking',
        'end_time > start_time'
    )
    
    op.create_check_constraint(
        'check_booking_price_positive',
        'booking',
        'total_price > 0'
    )
    
    op.create_check_constraint(
        'check_booking_hours_positive',
        'booking',
        'total_hours > 0'
    )
    
    op.create_check_constraint(
        'check_booking_status_valid',
        'booking',
        "status IN ('pending', 'confirmed', 'active', 'completed', 'cancelled', 'no_show', 'disputed', 'checked_out')"
    )
    
    op.create_check_constraint(
        'check_payment_status_valid',
        'booking',
        "payment_status IN ('pending', 'paid', 'failed', 'cancelled', 'refunded', 'on_hold')"
    )
    
    op.create_check_constraint(
        'check_booking_type_valid',
        'booking',
        "booking_type IN ('hourly', 'daily')"
    )
    
    # Add indexes for performance
    op.create_index('idx_booking_home_time', 'booking', ['home_id', 'start_time', 'end_time'])
    op.create_index('idx_booking_renter', 'booking', ['renter_id'])
    op.create_index('idx_booking_status', 'booking', ['status'])
    op.create_index('idx_booking_payment_status', 'booking', ['payment_status'])
    op.create_index('idx_booking_created_at', 'booking', ['created_at'])
    op.create_index('idx_booking_time_range', 'booking', ['start_time', 'end_time'])
    
    # Add unique constraint to prevent overlapping bookings
    # Note: This is a complex constraint that needs to be handled carefully
    # For SQLite, we'll use a trigger instead of a unique constraint
    # For PostgreSQL, we can use EXCLUDE constraint
    
    # Create a function to check for overlapping bookings (PostgreSQL)
    op.execute("""
        CREATE OR REPLACE FUNCTION check_booking_overlap()
        RETURNS TRIGGER AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM booking 
                WHERE home_id = NEW.home_id 
                AND id != COALESCE(NEW.id, 0)
                AND status IN ('pending', 'confirmed', 'active')
                AND (
                    (NEW.start_time < end_time AND NEW.end_time > start_time)
                )
            ) THEN
                RAISE EXCEPTION 'Booking time conflicts with existing booking';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for overlap checking
    op.execute("""
        CREATE TRIGGER trigger_check_booking_overlap
        BEFORE INSERT OR UPDATE ON booking
        FOR EACH ROW
        EXECUTE FUNCTION check_booking_overlap();
    """)


def downgrade():
    """Remove booking constraints and indexes"""
    
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS trigger_check_booking_overlap ON booking;")
    op.execute("DROP FUNCTION IF EXISTS check_booking_overlap();")
    
    # Drop indexes
    op.drop_index('idx_booking_time_range', 'booking')
    op.drop_index('idx_booking_created_at', 'booking')
    op.drop_index('idx_booking_payment_status', 'booking')
    op.drop_index('idx_booking_status', 'booking')
    op.drop_index('idx_booking_renter', 'booking')
    op.drop_index('idx_booking_home_time', 'booking')
    
    # Drop check constraints
    op.drop_constraint('check_booking_type_valid', 'booking')
    op.drop_constraint('check_payment_status_valid', 'booking')
    op.drop_constraint('check_booking_status_valid', 'booking')
    op.drop_constraint('check_booking_hours_positive', 'booking')
    op.drop_constraint('check_booking_price_positive', 'booking')
    op.drop_constraint('check_booking_time_valid', 'booking')
