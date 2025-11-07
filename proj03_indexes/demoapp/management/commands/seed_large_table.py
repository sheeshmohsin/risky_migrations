from django.core.management.base import BaseCommand
from demoapp.models import SmallEmail, LargeEmail


class Command(BaseCommand):
    help = 'Seeds the SmallEmail table with 10 rows and LargeEmail table with millions of rows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--large-count',
            type=int,
            default=5000000,
            help='Number of rows to create in LargeEmail table (default: 5,000,000)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000000,
            help='Batch size for bulk inserts (default: 1,000,000)'
        )

    def handle(self, *args, **options):
        large_count = options['large_count']
        batch_size = options['batch_size']

        self.stdout.write(self.style.SUCCESS('Seeding SmallEmail table...'))
        SmallEmail.objects.all().delete()
        small_emails = [
            SmallEmail(name=f'SmallUser_{i}', email=f'small{i}@example.com')
            for i in range(1, 11)
        ]
        SmallEmail.objects.bulk_create(small_emails)
        self.stdout.write(self.style.SUCCESS(f'Created {len(small_emails)} SmallEmail records'))

        self.stdout.write(self.style.SUCCESS(f'Seeding LargeEmail table with {large_count:,} rows...'))
        LargeEmail.objects.all().delete()

        # Create in batches to avoid memory issues
        total_created = 0
        for batch_start in range(0, large_count, batch_size):
            batch_end = min(batch_start + batch_size, large_count)
            large_emails = [
                LargeEmail(name=f'LargeUser_{i}', email=f'user{i}@example.com')
                for i in range(batch_start + 1, batch_end + 1)
            ]
            LargeEmail.objects.bulk_create(large_emails)
            total_created += len(large_emails)

            if total_created % 1000000 == 0:
                self.stdout.write(f'  Created {total_created:,} rows...')

        self.stdout.write(self.style.SUCCESS(f'Created {total_created:,} LargeEmail records'))
        self.stdout.write(self.style.SUCCESS('Seeding complete!'))
