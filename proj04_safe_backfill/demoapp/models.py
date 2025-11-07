from django.db import models
from django.utils import timezone


class SmallRecord(models.Model):
    """Small table with just 10 rows for comparison."""
    name = models.CharField(max_length=100)
    created_at = models.CharField(max_length=50)  # Initial state: CharField
    # created_at_new = models.DateTimeField(default=timezone.now)  # Step 3: After backfill, enforce NOT NULL

    class Meta:
        db_table = 'small_record'

    def __str__(self):
        return self.name


class LargeRecord(models.Model):
    """Large table with millions of rows to demonstrate safe column type change."""
    name = models.CharField(max_length=100)
    created_at = models.CharField(max_length=50)  # Initial state: CharField
    # created_at_new = models.DateTimeField(default=timezone.now)  # Step 3: After backfill, enforce NOT NULL

    class Meta:
        db_table = 'large_record'

    def __str__(self):
        return self.name
