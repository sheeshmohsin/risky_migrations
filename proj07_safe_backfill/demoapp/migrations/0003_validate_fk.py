# Manual migration to validate FK constraints
# This can be run during a maintenance window or low-traffic period

from django.db import migrations
from datetime import datetime


def log_smallorder_validate_start(apps, schema_editor):
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] Validating FK constraint on SmallOrder...")


def log_smallorder_validate_end(apps, schema_editor):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] ✓ SmallOrder FK constraint validated\n")


def log_largeorder_validate_start(apps, schema_editor):
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] Validating FK constraint on LargeOrder...")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] This will scan all rows in large_order table (may take 30-60 seconds)...")


def log_largeorder_validate_end(apps, schema_editor):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] ✓ LargeOrder FK constraint validated\n")


class Migration(migrations.Migration):

    dependencies = [
        ('demoapp', '0002_add_fk_not_valid'),
    ]

    operations = [
        # Validate SmallOrder FK
        migrations.RunPython(log_smallorder_validate_start, migrations.RunPython.noop),
        migrations.RunSQL(
            sql="""
                ALTER TABLE small_order VALIDATE CONSTRAINT demoapp_smallorder_customer_id_fkey;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
        migrations.RunPython(log_smallorder_validate_end, migrations.RunPython.noop),

        # Validate LargeOrder FK
        migrations.RunPython(log_largeorder_validate_start, migrations.RunPython.noop),
        migrations.RunSQL(
            sql="""
                ALTER TABLE large_order VALIDATE CONSTRAINT demoapp_largeorder_customer_id_fkey;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
        migrations.RunPython(log_largeorder_validate_end, migrations.RunPython.noop),
    ]
