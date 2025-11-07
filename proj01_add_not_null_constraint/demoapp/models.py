from django.db import models


class SmallUser(models.Model):
    """Small table with just 10 rows for comparison."""
    name = models.CharField(max_length=100)
    # status = models.CharField(max_length=20, null=True, blank=True)  # Start nullable

    class Meta:
        db_table = 'small_user'

    def __str__(self):
        return self.name


class LargeUser(models.Model):
    """Large table with millions of rows to demonstrate migration impact."""
    name = models.CharField(max_length=100)
    # status = models.CharField(max_length=20, null=True, blank=True)  # Start nullable

    class Meta:
        db_table = 'large_user'

    def __str__(self):
        return self.name
