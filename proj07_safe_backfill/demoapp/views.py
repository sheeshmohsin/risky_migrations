from django.http import JsonResponse
from .models import LargeOrder
from decimal import Decimal


def list_large(request):
    """
    Simple view to query the large table (READ operation).
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


def update_order(request):
    """
    Update an order's total_amount (WRITE operation).
    This will BLOCK during migration 0003 (VALIDATE CONSTRAINT).
    Demonstrates that VALIDATE blocks writes but not reads.
    """
    # Update the first order's amount
    order = LargeOrder.objects.first()
    if order:
        order.total_amount += Decimal('1.00')
        order.save()
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'new_amount': str(order.total_amount)
        })
    else:
        return JsonResponse({'success': False, 'error': 'No orders found'})
