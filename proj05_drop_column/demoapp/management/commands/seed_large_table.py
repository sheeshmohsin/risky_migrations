from django.core.management.base import BaseCommand
from demoapp.models import SmallProduct, LargeProduct
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seeds the SmallProduct table with 10 rows and LargeProduct table with millions of rows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--large-count',
            type=int,
            default=5000000,
            help='Number of rows to create in LargeProduct table (default: 5,000,000)'
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

        self.stdout.write(self.style.SUCCESS('Seeding SmallProduct table...'))
        SmallProduct.objects.all().delete()
        small_products = [
            SmallProduct(
                name=f'SmallProduct_{i}',
                legacy_code=f'LEGACY_{i:03d}',
                price=Decimal('10.99') + Decimal(i)
            )
            for i in range(1, 11)
        ]
        SmallProduct.objects.bulk_create(small_products)
        self.stdout.write(self.style.SUCCESS(f'Created {len(small_products)} SmallProduct records'))

        self.stdout.write(self.style.SUCCESS(f'Seeding LargeProduct table with {large_count:,} rows...'))
        LargeProduct.objects.all().delete()

        # Create in batches to avoid memory issues
        total_created = 0
        for batch_start in range(0, large_count, batch_size):
            batch_end = min(batch_start + batch_size, large_count)
            large_products = [
                LargeProduct(
                    name=f'LargeProduct_{i}',
                    legacy_code=f'LEGACY_{i:010d}',
                    price=Decimal('19.99') + Decimal(i % 100)
                )
                for i in range(batch_start + 1, batch_end + 1)
            ]
            LargeProduct.objects.bulk_create(large_products)
            total_created += len(large_products)

            if total_created % 1000000 == 0:
                self.stdout.write(f'  Created {total_created:,} rows...')

        self.stdout.write(self.style.SUCCESS(f'Created {total_created:,} LargeProduct records'))
        self.stdout.write(self.style.SUCCESS('Seeding complete!'))
