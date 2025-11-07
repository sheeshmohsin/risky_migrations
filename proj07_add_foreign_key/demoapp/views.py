from django.http import JsonResponse
from .models import LargeOrder


def list_large(request):
    """
    Simple view to query the large table.
    Use this to test table locking during migration.
    """
    orders = LargeOrder.objects.all()[:10]
    data = [
        {
            'id': o.id,
            'order_number': o.order_number,
            'customer_id': o.customer_id,
            'total_amount': str(o.total_amount)
        }
        for o in orders
    ]
    return JsonResponse({'orders': data, 'count': len(data)})
