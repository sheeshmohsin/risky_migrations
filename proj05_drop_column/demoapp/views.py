from django.http import JsonResponse
from .models import LargeProduct


def list_large(request):
    """
    Simple view to query the large table.
    Use this to test table locking during migration.
    """
    # Use values() to only fetch fields that definitely exist
    # This prevents Django from trying to fetch legacy_code if it's been dropped
    products = LargeProduct.objects.values('id', 'name', 'price')[:10]
    data = [
        {
            'id': p['id'],
            'name': p['name'],
            'legacy_code': 'N/A',  # Always N/A since we're not fetching it
            'price': str(p['price'])
        }
        for p in products
    ]
    return JsonResponse({'products': data, 'count': len(data)})


def search_by_legacy_code(request):
    """
    RISKY: This endpoint uses legacy_code column.
    This will BREAK if the column is dropped before removing this code!

    Demonstrates why you must remove all code references BEFORE dropping a column.
    """
    legacy_code = request.GET.get('code', 'LEGACY-001')

    # This will fail with ProgrammingError if legacy_code column is dropped
    products = LargeProduct.objects.filter(legacy_code=legacy_code)[:10]

    data = [
        {
            'id': p.id,
            'name': p.name,
            'legacy_code': p.legacy_code,
            'price': str(p.price)
        }
        for p in products
    ]

    return JsonResponse({
        'query': legacy_code,
        'products': data,
        'count': len(data)
    })
