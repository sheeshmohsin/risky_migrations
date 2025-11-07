from django.db import models


class SmallProduct(models.Model):
    """Small table with just 10 rows for comparison."""
    name = models.CharField(max_length=100)
    legacy_code = models.CharField(max_length=50)  # WRONG WAY: Dropped directly in migration 0002
    # legacy_code_deprecated = models.CharField(max_length=50, null=True, blank=True)  # RIGHT WAY: Step 1 - Mark as deprecated (nullable), Step 2 - Drop after code updated
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'small_product'

    def __str__(self):
        return self.name


class LargeProduct(models.Model):
    """Large table with millions of rows to demonstrate column drop impact."""
    name = models.CharField(max_length=100)
    legacy_code = models.CharField(max_length=50)  # WRONG WAY: Dropped directly in migration 0002
    # legacy_code_deprecated = models.CharField(max_length=50, null=True, blank=True)  # RIGHT WAY: Step 1 - Mark as deprecated (nullable), Step 2 - Drop after code updated
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'large_product'

    def __str__(self):
        return self.name
