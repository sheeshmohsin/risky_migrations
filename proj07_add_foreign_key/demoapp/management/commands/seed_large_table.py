from django.core.management.base import BaseCommand
from demoapp.models import Customer, SmallOrder, LargeOrder
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seeds Customer, SmallOrder (10 rows), and LargeOrder (millions of rows)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--large-count',
            type=int,
            default=5000000,
            help='Number of rows to create in LargeOrder table (default: 5,000,000)'
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

        # Seed Customers first
        self.stdout.write(self.style.SUCCESS('Seeding Customer table...'))
        Customer.objects.all().delete()
        customers = [
            Customer(name=f'Customer_{i}', email=f'customer{i}@example.com')
            for i in range(1, 101)  # Create 100 customers
        ]
        Customer.objects.bulk_create(customers)
        self.stdout.write(self.style.SUCCESS(f'Created {len(customers)} Customer records'))

        # Get customer IDs for reference
        customer_ids = list(Customer.objects.values_list('id', flat=True))

        # Seed SmallOrder
        self.stdout.write(self.style.SUCCESS('Seeding SmallOrder table...'))
        SmallOrder.objects.all().delete()
        small_orders = [
            SmallOrder(
                order_number=f'SMALL-{i:05d}',
                customer_id=customer_ids[i % len(customer_ids)],
                total_amount=Decimal('50.00') + Decimal(i * 10)
            )
            for i in range(1, 11)
        ]
        SmallOrder.objects.bulk_create(small_orders)
        self.stdout.write(self.style.SUCCESS(f'Created {len(small_orders)} SmallOrder records'))

        # Seed LargeOrder
        self.stdout.write(self.style.SUCCESS(f'Seeding LargeOrder table with {large_count:,} rows...'))
        LargeOrder.objects.all().delete()

        # Create in batches to avoid memory issues
        total_created = 0
        for batch_start in range(0, large_count, batch_size):
            batch_end = min(batch_start + batch_size, large_count)
            large_orders = [
                LargeOrder(
                    order_number=f'LARGE-{i:010d}',
                    customer_id=customer_ids[i % len(customer_ids)],
                    total_amount=Decimal('100.00') + Decimal(i % 1000)
                )
                for i in range(batch_start + 1, batch_end + 1)
            ]
            LargeOrder.objects.bulk_create(large_orders)
            total_created += len(large_orders)

            if total_created % 100000 == 0:
                self.stdout.write(f'  Created {total_created:,} rows...')

        self.stdout.write(self.style.SUCCESS(f'Created {total_created:,} LargeOrder records'))
        self.stdout.write(self.style.SUCCESS('Seeding complete!'))
