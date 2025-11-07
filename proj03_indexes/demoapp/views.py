from django.http import JsonResponse
from django.db import transaction
from .models import LargeEmail
import random


def list_large(request):
    """
    Endpoint to query the large table with a write operation.
    During migration, the UPDATE will block due to table locks,
    demonstrating real-world production impact.
    """
    # Step 1: Perform a write operation (UPDATE)
    # Pick a random row and update it to simulate real traffic
    random_id = random.randint(1, 1000)
    with transaction.atomic():
        LargeEmail.objects.filter(id=random_id).update(
            email=f'updated_{random_id}@example.com'
        )

    # Step 2: Perform read operation
    emails = LargeEmail.objects.all()[:10]
    data = [{'id': email.id, 'name': email.name, 'email': email.email} for email in emails]

    return JsonResponse({
        'emails': data,
        'count': len(data),
        'updated_id': random_id
    })
