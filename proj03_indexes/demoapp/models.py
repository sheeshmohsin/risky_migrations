from django.db import models


class SmallEmail(models.Model):
    """Small table with just 10 rows for comparison."""
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'small_email'

    def __str__(self):
        return self.email


class LargeEmail(models.Model):
    """Large table with millions of rows to demonstrate index creation impact."""
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'large_email'

    def __str__(self):
        return self.email
