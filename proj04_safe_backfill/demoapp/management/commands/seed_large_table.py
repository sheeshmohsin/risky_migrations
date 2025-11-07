from django.core.management.base import BaseCommand
from demoapp.models import SmallRecord, LargeRecord
from datetime import datetime


class Command(BaseCommand):
    help = 'Seeds the SmallRecord table with 10 rows and LargeRecord table with millions of rows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--large-count',
            type=int,
            default=5000000,
            help='Number of rows to create in LargeRecord table (default: 5,000,000)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10000,
            help='Batch size for bulk inserts (default: 10,000)'
        )

    def handle(self, *args, **options):
        large_count = options['large_count']
        batch_size = options['batch_size']

        self.stdout.write(self.style.SUCCESS('Seeding SmallRecord table...'))
        SmallRecord.objects.all().delete()
        # Store as string in format "YYYY-MM-DD HH:MM:SS" since it's a CharField
        small_records = [
            SmallRecord(name=f'SmallRecord_{i}', created_at='2024-01-01 10:00:00')
            for i in range(1, 11)
        ]
        SmallRecord.objects.bulk_create(small_records, ignore_conflicts=False)
        self.stdout.write(self.style.SUCCESS(f'Created {len(small_records)} SmallRecord records'))

        self.stdout.write(self.style.SUCCESS(f'Seeding LargeRecord table with {large_count:,} rows...'))
        LargeRecord.objects.all().delete()

        # Create in batches to avoid memory issues
        total_created = 0
        for batch_start in range(0, large_count, batch_size):
            batch_end = min(batch_start + batch_size, large_count)
            large_records = [
                LargeRecord(
                    name=f'LargeRecord_{i}',
                    # Store dates as strings in format "YYYY-MM-DD HH:MM:SS"
                    created_at=f'2024-01-{((i % 28) + 1):02d} 10:00:00'
                )
                for i in range(batch_start + 1, batch_end + 1)
            ]
            LargeRecord.objects.bulk_create(large_records, ignore_conflicts=False)
            total_created += len(large_records)

            if total_created % 100000 == 0:
                self.stdout.write(f'  Created {total_created:,} rows...')

        self.stdout.write(self.style.SUCCESS(f'Created {total_created:,} LargeRecord records'))
        self.stdout.write(self.style.SUCCESS('Seeding complete!'))
