# views_search_addon.py - Fuzzy Search Views
"""
Bu faylni views.py ga qo'shing yoki alohida views module qiling
"""

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q, Count
from .models import Mahsulot
from .search_utils import (
    normalize_uzbek_text,
    uzbek_stemmer,
    smart_match,
    rank_results,
    autocomplete_suggestions,
    combined_similarity,
    SearchHistory,
)

# Global search history (production da Redis/Database ishlatiladi)
search_history = SearchHistory()


@require_GET
def api_search_fuzzy(request):
    """
    Advanced Fuzzy Search API
    
    Xususiyatlar:
    - Typo tolerance ("ktob" → "kitob")
    - Plural/singular matching ("kitob" ↔ "kitoblar")
    - Partial matching ("iph" → "iphone")
    - Smart ranking (similarity + premium + popularity)
    - No duplicate results
    
    GET parametrlar:
    - q: qidiruv so'zi (required)
    - limit: natijalar soni (default: 20)
    - threshold: minimum similarity % (default: 60)
    
    Qaytaradi: JSON
    """
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 20))
    threshold = float(request.GET.get('threshold', 60.0))
    
    if len(query) < 2:
        return JsonResponse({
            'success': True,
            'count': 0,
            'results': [],
            'suggestions': [],
            'message': 'Kamida 2 ta harf kiriting'
        })
    
    try:
        # Qidiruvni tarixga saqlash
        search_history.add_search(query)
        
        # Query normalizatsiyasi
        query_normalized = normalize_uzbek_text(query)
        query_stem = uzbek_stemmer(query_normalized)
        
        print(f"[FUZZY SEARCH] Query: '{query}' → Normalized: '{query_normalized}' → Stem: '{query_stem}'")
        
        # 1. DATABASE SEARCH - barcha aktiv mahsulotlar
        all_products = Mahsulot.objects.filter(
            aktiv=True,
            sotilgan=False
        ).select_related('user').values(
            'id', 'name', 'narx', 'category', 'tavsif', 
            'asosiyimg', 'viloyat', 'is_premium', 'premium_priority',
            'korishlar_soni', 'mahsulotturi'
        )[:500]  # First 500 products to check
        
        # 2. SMART MATCHING va SCORING
        matched_products = []
        seen_ids = set()
        
        for product in all_products:
            # Duplicate check
            if product['id'] in seen_ids:
                continue
            
            # Smart matching
            name_match, name_sim = smart_match(query, product['name'], threshold=0)
            cat_match, cat_sim = smart_match(query, product['category'], threshold=0)
            type_match, type_sim = smart_match(query, product['mahsulotturi'], threshold=0)
            
            # Description matching (ixtiyoriy)
            desc_sim = 0.0
            if product.get('tavsif'):
                desc_match, desc_sim = smart_match(query, product['tavsif'][:200], threshold=0)
            
            # Weighted score
            score = (
                name_sim * 0.50 +      # Name eng muhim
                cat_sim * 0.20 +       # Category
                type_sim * 0.20 +      # Mahsulot turi
                desc_sim * 0.10        # Description
            )
            
            # Threshold check
            if score < threshold:
                continue
            
            # Premium bonus
            if product.get('is_premium', False):
                score *= 1.15  # 15% bonus
            
            # Popularity bonus
            views = product.get('korishlar_soni', 0)
            if views > 50:
                score *= 1.02
            if views > 200:
                score *= 1.05
            if views > 500:
                score *= 1.10
            
            # Match type aniqlash
            match_type = 'fuzzy'
            if name_sim >= 95:
                match_type = 'exact'
            elif name_sim >= 80:
                match_type = 'high'
            elif name_sim >= 65:
                match_type = 'medium'
            
            # Result object
            result = {
                'id': product['id'],
                'name': product['name'],
                'price': format_price(product.get('narx', '0')),
                'category': product['category'],
                'category_display': get_category_display(product['category']),
                'image': product.get('asosiyimg', ''),
                'url': f"/mahsulot/{product['id']}/",
                'is_premium': product.get('is_premium', False),
                'viloyat': product.get('viloyat', ''),
                # Search metadata
                'score': round(score, 2),
                'name_similarity': round(name_sim, 2),
                'category_similarity': round(cat_sim, 2),
                'match_type': match_type,
            }
            
            matched_products.append(result)
            seen_ids.add(product['id'])
        
        # 3. RANKING - score bo'yicha saralash
        matched_products.sort(key=lambda x: -x['score'])
        
        # 4. LIMIT
        top_results = matched_products[:limit]
        
        # 5. SUGGESTIONS - agar kam natija topilsa
        suggestions = []
        if len(top_results) < 3:
            # Ko'p qidirilgan so'zlardan takliflar
            popular = search_history.get_popular(limit=5)
            for term, count in popular:
                if term != query_normalized:
                    sim = combined_similarity(query_normalized, term)
                    if sim >= 60:
                        suggestions.append({
                            'text': term,
                            'similarity': round(sim, 2),
                            'searches': count
                        })
        
        # 6. RESPONSE
        response = {
            'success': True,
            'query': query,
            'normalized_query': query_normalized,
            'count': len(top_results),
            'total_matched': len(matched_products),
            'results': top_results,
            'suggestions': suggestions[:3],
            'threshold': threshold,
        }
        
        # Debug info (development only)
        if request.GET.get('debug') == '1':
            response['debug'] = {
                'query_stem': query_stem,
                'total_products_checked': len(all_products),
                'matched_before_limit': len(matched_products),
            }
        
        return JsonResponse(response)
        
    except Exception as e:
        print(f"[FUZZY SEARCH ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': str(e),
            'query': query,
            'results': []
        })


@require_GET
def api_autocomplete(request):
    """
    Autocomplete API - realtime suggestions
    
    Foydalanuvchi yozayotganda takliflar chiqaradi
    
    GET parametrlar:
    - q: qidiruv so'zi
    - limit: maksimal takliflar soni (default: 10)
    
    Qaytaradi:
    - suggestions: takliflar ro'yxati
    """
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 10))
    
    if len(query) < 1:
        return JsonResponse({
            'success': True,
            'suggestions': [],
            'popular': search_history.get_popular(limit=5)
        })
    
    try:
        query_normalized = normalize_uzbek_text(query)
        
        # 1. Mahsulot nomlarini olish
        product_names = Mahsulot.objects.filter(
            aktiv=True,
            sotilgan=False
        ).values_list('name', flat=True).distinct()[:200]
        
        # 2. Autocomplete suggestions
        suggestions = autocomplete_suggestions(
            query=query,
            products=list(product_names),
            max_suggestions=limit
        )
        
        # 3. Kategoriyalardan ham qidirish
        categories = Mahsulot.objects.filter(
            aktiv=True,
            sotilgan=False
        ).values_list('category', flat=True).distinct()
        
        category_suggestions = []
        for cat in categories:
            if query_normalized in normalize_uzbek_text(cat):
                category_suggestions.append({
                    'text': get_category_display(cat),
                    'type': 'category',
                    'url': f'/kategoriya/{cat}/'
                })
        
        # 4. Response
        return JsonResponse({
            'success': True,
            'query': query,
            'suggestions': [{'text': s, 'type': 'product'} for s in suggestions],
            'categories': category_suggestions[:3],
            'count': len(suggestions) + len(category_suggestions)
        })
        
    except Exception as e:
        print(f"[AUTOCOMPLETE ERROR] {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'suggestions': []
        })


@require_GET
def api_search_suggestions(request):
    """
    "Did you mean?" suggestions
    
    Agar foydalanuvchi xato yozgan bo'lsa, to'g'ri variantlarni taklif qiladi
    
    GET parametrlar:
    - q: xato yozilgan so'z
    - limit: maksimal takliflar (default: 5)
    
    Qaytaradi:
    - corrections: to'g'ri yozilish variantlari
    """
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 5))
    
    if len(query) < 2:
        return JsonResponse({
            'success': True,
            'corrections': []
        })
    
    try:
        query_normalized = normalize_uzbek_text(query)
        
        # 1. Barcha mahsulot nomlarini olish
        product_names = set(
            Mahsulot.objects.filter(
                aktiv=True,
                sotilgan=False
            ).values_list('name', flat=True).distinct()
        )
        
        # 2. Eng yaqin so'zlarni topish
        corrections = []
        for name in product_names:
            similarity = combined_similarity(query_normalized, name)
            
            # 40-100% o'rtasida (to'g'ri emas lekin yaqin)
            if 40 <= similarity < 100:
                corrections.append({
                    'text': name,
                    'similarity': round(similarity, 2),
                    'type': 'product'
                })
        
        # 3. Similarity bo'yicha saralash
        corrections.sort(key=lambda x: -x['similarity'])
        
        # 4. Response
        return JsonResponse({
            'success': True,
            'query': query,
            'corrections': corrections[:limit],
            'message': "Balki shu mahsulotlarni qidirgandirsiz?" if corrections else None
        })
        
    except Exception as e:
        print(f"[SUGGESTIONS ERROR] {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'corrections': []
        })


@require_GET
def api_popular_searches(request):
    """
    Ko'p qidirilgan so'zlar
    
    GET parametrlar:
    - limit: maksimal so'zlar soni (default: 20)
    
    Qaytaradi:
    - popular: ko'p qidirilgan so'zlar va ularning soni
    """
    limit = int(request.GET.get('limit', 20))
    
    try:
        popular = search_history.get_popular(limit=limit)
        
        return JsonResponse({
            'success': True,
            'popular': [
                {
                    'text': term,
                    'count': count,
                    'url': f'/barcha-mahsulotlar/?q={term}'
                }
                for term, count in popular
            ]
        })
        
    except Exception as e:
        print(f"[POPULAR SEARCHES ERROR] {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'popular': []
        })


# ==================== HELPER FUNCTIONS ====================

def format_price(narx):
    """Narxni formatlash"""
    try:
        if not narx:
            return "0 so'm"
        
        import re
        narx_str = str(narx).replace(',', '.').strip()
        narx_str = re.sub(r'[^\d.]', '', narx_str)
        
        if narx_str and narx_str != '.':
            narx_float = float(narx_str)
            if narx_float.is_integer():
                return f"{int(narx_float):,} so'm".replace(',', ' ')
            else:
                return f"{narx_float:,.2f} so'm".replace(',', ' ')
        
        return "0 so'm"
    except:
        return "0 so'm"


def get_category_display(category):
    """Kategoriya nomini olish"""
    categories = {
        'elektronika': 'Elektronika',
        'kitob': 'Kitoblar',
        'mebel': 'Mebellar',
        'cheteltovarlar': 'Chet el tovarlari',
        'uyjoyelonlari': 'Uy-joy',
        'onavabollar': 'Onalar va bolalar',
        'avto_elonlari': 'Auto',
        'uy_jihozlari': 'Uy jihozlari',
        'kiyim': 'Kiyim-kechak',
        'avto': 'Avto qismlar',
        'boshqa': 'Boshqa',
    }
    return categories.get(category, category)