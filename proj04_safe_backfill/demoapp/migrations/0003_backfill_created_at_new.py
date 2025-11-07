from django.db import migrations
from datetime import datetime
from django.utils import timezone


def backfill_created_at_new(apps, schema_editor):
    """Backfill created_at_new from created_at in batches."""
    SmallRecord = apps.get_model('demoapp', 'SmallRecord')
    LargeRecord = apps.get_model('demoapp', 'LargeRecord')

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting backfill for SmallRecord...")
    small_records = SmallRecord.objects.all()
    for record in small_records:
        # Convert string date to DateTimeField
        record.created_at_new = timezone.make_aware(datetime.strptime(record.created_at, '%Y-%m-%d %H:%M:%S'))
    SmallRecord.objects.bulk_update(small_records, ['created_at_new'])
    print(f"[{datetime.now().strftime('%H:%M:%S')}] SmallRecord backfill complete: {len(small_records)} rows")

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting batch backfill for LargeRecord...")
    batch_size = 10000
    total_backfilled = 0
    batch_num = 0

    while True:
        batch_start = datetime.now()

        # Use raw SQL for much faster updates
        # PostgreSQL can convert VARCHAR to TIMESTAMP directly
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE large_record
                SET created_at_new = created_at::timestamp
                WHERE id IN (
                    SELECT id FROM large_record
                    WHERE created_at_new IS NULL
                    LIMIT %s
                )
            """, [batch_size])
            updated = cursor.rowcount

        if updated == 0:
            break

        total_backfilled += updated
        batch_num += 1
        batch_duration = (datetime.now() - batch_start).total_seconds()

        # Print progress every 10 batches
        if batch_num % 10 == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Batch {batch_num}: "
                  f"Updated {updated:,} rows in {batch_duration:.2f}s "
                  f"(Total: {total_backfilled:,})")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] LargeRecord backfill complete! Total: {total_backfilled:,} rows")


def reverse_backfill(apps, schema_editor):
    """Clear created_at_new values on rollback."""
    SmallRecord = apps.get_model('demoapp', 'SmallRecord')
    LargeRecord = apps.get_model('demoapp', 'LargeRecord')

    SmallRecord.objects.update(created_at_new=None)
    LargeRecord.objects.update(created_at_new=None)


class Migration(migrations.Migration):

    dependencies = [
        ('demoapp', '0002_largerecord_created_at_new_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_created_at_new, reverse_backfill),
    ]
