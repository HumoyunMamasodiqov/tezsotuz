# views_search_addon.py - Fuzzy Search Views

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q, Count
from .models import Mahsulot
from .search_service import SearchService


@require_GET
def api_search_fuzzy(request):
    """Advanced Fuzzy Search API"""
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 20))
    
    if len(query) < 2:
        return JsonResponse({'success': True, 'count': 0, 'results': [], 'suggestions': []})
    
    try:
        results = SearchService.fuzzy_search(query)
        products_data = []
        for product in results[:limit]:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'price': product.narx_formatted(),
                'category': product.get_category_display(),
                'image': product.asosiyimg.url if product.asosiyimg else None,
                'url': f"/mahsulot/{product.id}/",
                'is_premium': product.is_premium,
                'viloyat': product.get_viloyat_display() if product.viloyat else '',
            })
        
        return JsonResponse({'success': True, 'count': len(products_data), 'results': products_data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'results': []})


@require_GET
def api_autocomplete(request):
    """Autocomplete API"""
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 10))
    
    if len(query) < 1:
        return JsonResponse({'success': True, 'suggestions': []})
    
    try:
        suggestions = SearchService.get_suggestions(query)
        return JsonResponse({
            'success': True,
            'suggestions': [{'text': s, 'type': 'product'} for s in suggestions[:limit]]
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'suggestions': []})
