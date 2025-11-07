from django.http import JsonResponse
from .models import LargeUser


def list_large(request):
    """
    Endpoint to query the large table.
    During migration, this will block due to table locks.
    """
    users = LargeUser.objects.all()[:10]
    data = [{'id': user.id, 'name': user.name} for user in users]
    return JsonResponse({'users': data, 'count': len(data)})
