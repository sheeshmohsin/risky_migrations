# Custom migration to add index using CREATE INDEX CONCURRENTLY
from django.db import migrations
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import models


class Migration(migrations.Migration):
    atomic = False  # CONCURRENTLY cannot run in a transaction

    dependencies = [
        ('demoapp', '0001_initial'),
    ]

    operations = [
        # Add index to SmallEmail.email using CONCURRENTLY
        AddIndexConcurrently(
            model_name='smallemail',
            index=models.Index(fields=['email'], name='small_email_email_idx'),
        ),
        # Add index to LargeEmail.email using CONCURRENTLY
        AddIndexConcurrently(
            model_name='largeemail',
            index=models.Index(fields=['email'], name='large_email_email_idx'),
        ),
    ]
