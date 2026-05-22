# search_service.py - To'liq ishlaydigan versiya

import re
from django.db.models import Q

class SearchService:
    """Professional qidiruv xizmati"""
    
    # O'zbekcha qo'shimchalar
    UZBEK_SUFFIXES = [
        'lar', 'ning', 'ga', 'ni', 'da', 'dan', 'miz', 'siz', 'iz',
        'lik', 'chi', 'dor', 'li', 'siz', 'im', 'ing', 'di', 'gan',
        'mi', 'si', 'ki', 'dek', 'day', 'cha', 'gacha'
    ]
    
    # Xato yozilgan so'zlar
    COMMON_TYPOS = {
        'ktob': 'kitob',
        'kito': 'kitob',
        'kitp': 'kitob',
        'kitoblar': 'kitob',
        'kitobl': 'kitob',
        'samzung': 'samsung',
        'samsng': 'samsung',
        'samsun': 'samsung',
        'aple': 'apple',
        'apl': 'apple',
        'iphn': 'iphone',
        'iphon': 'iphone',
        'mashna': 'mashina',
        'moshna': 'mashina',
        'masina': 'mashina',
        'mashinka': 'mashina',
        'telifon': 'telefon',
        'telafon': 'telefon',
        'telefonlar': 'telefon',
        'noutbik': 'noutbuk',
        'noytbook': 'noutbuk',
        'nout': 'noutbuk',
        'komp': 'kompyuter',
        'kompyutr': 'kompyuter',
        'plansh': 'planshet',
        'planshet': 'planshet',
    }
    
    @classmethod
    def normalize_word(cls, word):
        """So'zni normalize qilish"""
        if not word:
            return ""
        
        word = word.lower().strip()
        
        # Xatoliklarni tuzatish
        if word in cls.COMMON_TYPOS:
            word = cls.COMMON_TYPOS[word]
        
        # Qo'shimchalarni olib tashlash
        for suffix in cls.UZBEK_SUFFIXES:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                word = word[:-len(suffix)]
                break
        
        return word
    
    @classmethod
    def levenshtein_distance(cls, s1, s2):
        """Levenshtein masofasi"""
        if len(s1) < len(s2):
            return cls.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @classmethod
    def calculate_similarity(cls, query, text):
        """O'xshashlik foizini hisoblash"""
        if not query or not text:
            return 0
        
        query = cls.normalize_word(query)
        text = cls.normalize_word(text)
        
        if not query or not text:
            return 0
        
        if query == text:
            return 100
        
        if query in text or text in query:
            return 85
        
        distance = cls.levenshtein_distance(query, text)
        max_len = max(len(query), len(text))
        
        if max_len == 0:
            return 100
        
        similarity = (1 - distance / max_len) * 100
        
        if query and text and query[0] == text[0]:
            similarity += 5
        
        return min(100, similarity)
    
    @classmethod
    def fuzzy_search(cls, query):
        """Fuzzy search"""
        from .models import Mahsulot
        
        if not query or len(query) < 2:
            return Mahsulot.objects.filter(aktiv=True, sotilgan=False).order_by('-is_premium', '-sana')
        
        # Barcha mahsulotlarni olish
        products = Mahsulot.objects.filter(aktiv=True, sotilgan=False)
        
        scored_products = []
        
        for product in products:
            # Nom bo'yicha
            name_sim = cls.calculate_similarity(query, product.name)
            
            # Kategoriya bo'yicha
            cat_sim = cls.calculate_similarity(query, product.category)
            
            # Tavsif bo'yicha
            desc_sim = 0
            if product.tavsif:
                desc_sim = cls.calculate_similarity(query, product.tavsif[:200])
            
            # Umumiy score
            final_score = max(name_sim, cat_sim * 0.7, desc_sim * 0.5)
            
            if final_score >= 20:
                scored_products.append((product, final_score))
        
        # Saralash
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        # Mahsulotlarni qaytarish
        from django.db.models import Case, When, Value, IntegerField
        product_ids = [p[0].id for p in scored_products[:100]]
        
        if product_ids:
            preserved = Case(*[When(id=id, then=pos) for pos, id in enumerate(product_ids)])
            return Mahsulot.objects.filter(id__in=product_ids).order_by(preserved)
        
        return Mahsulot.objects.none()
    
    @classmethod
    def get_suggestions(cls, query):
        """Qidiruv takliflari"""
        from .models import Mahsulot
        
        query = cls.normalize_word(query)
        if len(query) < 2:
            return []
        
        suggestions = set()
        
        # Typo takliflari
        for typo, correction in cls.COMMON_TYPOS.items():
            if query == typo or query in typo:
                suggestions.add(correction)
        
        # Mahsulot nomlaridan takliflar
        products = Mahsulot.objects.filter(aktiv=True, sotilgan=False)[:50]
        for product in products:
            name = cls.normalize_word(product.name)
            if cls.calculate_similarity(query, name) >= 50:
                suggestions.add(product.name)
        
        return list(suggestions)[:5]