from django.db import models


class Customer(models.Model):
    """Customer table - referenced by orders."""
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    class Meta:
        db_table = 'customer'

    def __str__(self):
        return self.name


class SmallOrder(models.Model):
    """Small table with just 10 rows for comparison."""
    order_number = models.CharField(max_length=50, unique=True)
    customer_id = models.IntegerField()  # Will add FK constraint via migration
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'small_order'

    def __str__(self):
        return self.order_number


class LargeOrder(models.Model):
    """Large table with millions of rows to demonstrate safe FK addition."""
    order_number = models.CharField(max_length=50, unique=True)
    customer_id = models.IntegerField()  # Initial state: plain integer
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'large_order'

    def __str__(self):
        return self.order_number
