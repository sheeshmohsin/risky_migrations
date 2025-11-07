from django.http import JsonResponse
from .models import LargeRecord


def list_large(request):
    """
    Endpoint to query the large table.
    During migration, this will block due to table locks.
    """
    records = LargeRecord.objects.all()[:10]
    data = [{'id': record.id, 'name': record.name, 'created_at': record.created_at} for record in records]
    return JsonResponse({'records': data, 'count': len(data)})
