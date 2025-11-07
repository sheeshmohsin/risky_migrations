from django.db import models


class SmallRecord(models.Model):
    """Small table with just 10 rows for comparison."""
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField()  # Changed from CharField - WRONG WAY
    # created_at_new = models.DateTimeField()  # After backfill: enforce NOT NULL

    class Meta:
        db_table = 'small_record'

    def __str__(self):
        return self.name


class LargeRecord(models.Model):
    """Large table with millions of rows to demonstrate column type change impact."""
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField()  # Changed from CharField - WRONG WAY
    # created_at_new = models.DateTimeField()  # After backfill: enforce NOT NULL

    class Meta:
        db_table = 'large_record'

    def __str__(self):
        return self.name
