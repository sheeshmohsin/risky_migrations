# Manual migration for safe FK addition using PostgreSQL's NOT VALID feature
# NOTE: Django doesn't have native support for FK NOT VALID, so we use raw SQL

from django.db import migrations
from datetime import datetime


def log_smallorder_start(apps, schema_editor):
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] Adding FK constraint to SmallOrder as NOT VALID (instant)...")


def log_smallorder_end(apps, schema_editor):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] ✓ SmallOrder FK constraint added (NOT VALID)\n")


def log_largeorder_start(apps, schema_editor):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] Adding FK constraint to LargeOrder as NOT VALID (instant)...")


def log_largeorder_end(apps, schema_editor):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] ✓ LargeOrder FK constraint added (NOT VALID)\n")


class Migration(migrations.Migration):

    dependencies = [
        ('demoapp', '0001_initial'),
    ]

    operations = [
        # SmallOrder: Add FK as NOT VALID
        migrations.RunPython(log_smallorder_start, migrations.RunPython.noop),
        migrations.RunSQL(
            sql="""
                ALTER TABLE small_order
                ADD CONSTRAINT demoapp_smallorder_customer_id_fkey
                FOREIGN KEY (customer_id) REFERENCES customer(id)
                NOT VALID;
            """,
            reverse_sql="""
                ALTER TABLE small_order DROP CONSTRAINT IF EXISTS demoapp_smallorder_customer_id_fkey;
            """
        ),
        migrations.RunPython(log_smallorder_end, migrations.RunPython.noop),

        # LargeOrder: Add FK as NOT VALID
        migrations.RunPython(log_largeorder_start, migrations.RunPython.noop),
        migrations.RunSQL(
            sql="""
                ALTER TABLE large_order
                ADD CONSTRAINT demoapp_largeorder_customer_id_fkey
                FOREIGN KEY (customer_id) REFERENCES customer(id)
                NOT VALID;
            """,
            reverse_sql="""
                ALTER TABLE large_order DROP CONSTRAINT IF EXISTS demoapp_largeorder_customer_id_fkey;
            """
        ),
        migrations.RunPython(log_largeorder_end, migrations.RunPython.noop),
    ]
