from django.core.management.base import BaseCommand
from demoapp.models import SmallUser, LargeUser


class Command(BaseCommand):
    help = 'Seeds the SmallUser table with 10 rows and LargeUser table with millions of rows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--large-count',
            type=int,
            default=100000000,
            help='Number of rows to create in LargeUser table (default: 100,000,000)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100000,
            help='Batch size for bulk inserts (default: 100,000)'
        )

    def handle(self, *args, **options):
        large_count = options['large_count']
        batch_size = options['batch_size']

        self.stdout.write(self.style.SUCCESS('Seeding SmallUser table...'))
        SmallUser.objects.all().delete()
        small_users = [SmallUser(name=f'SmallUser_{i}') for i in range(1, 11)]
        SmallUser.objects.bulk_create(small_users)
        self.stdout.write(self.style.SUCCESS(f'Created {len(small_users)} SmallUser records'))

        self.stdout.write(self.style.SUCCESS(f'Seeding LargeUser table with {large_count:,} rows...'))
        LargeUser.objects.all().delete()

        # Create in batches to avoid memory issues
        total_created = 0
        for batch_start in range(0, large_count, batch_size):
            batch_end = min(batch_start + batch_size, large_count)
            large_users = [
                LargeUser(name=f'LargeUser_{i}')
                for i in range(batch_start + 1, batch_end + 1)
            ]
            LargeUser.objects.bulk_create(large_users)
            total_created += len(large_users)

            if total_created % 10000000 == 0:
                self.stdout.write(f'  Created {total_created:,} rows...')

        self.stdout.write(self.style.SUCCESS(f'Created {total_created:,} LargeUser records'))
        self.stdout.write(self.style.SUCCESS('Seeding complete!'))
