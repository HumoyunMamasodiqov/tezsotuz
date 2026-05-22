from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponseNotFound, JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, F
from django.urls import reverse
from django.core.exceptions import PermissionDenied
import json
import re
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.models import User
from datetime import timedelta
from decimal import Decimal

# Import modellar
from .models import (
    Mahsulot, Sevimli, Category, Banner, SellerProfile, 
    PremiumUser, PremiumProduct, AdminPremiumSettings, 
    AdminAloqa, PremiumRequest, PremiumNotification
)

# ==================== HELPER FUNCTIONS ====================
def reklama(request):
    """Reklama sahifasi"""
    return render(request, 'reklama.html')
def is_admin(user):
    """Foydalanuvchi admin ekanligini tekshirish"""
    return user.is_superuser or user.is_staff or user.groups.filter(name='Admin').exists()

def is_premium_user(user):
    """Foydalanuvchi premium ekanligini tekshirish"""
    try:
        premium_profile = PremiumUser.objects.get(user=user)
        return premium_profile.is_premium
    except PremiumUser.DoesNotExist:
        return False

def check_premium_access(user):
    """Premium huquqini tekshirish va sababni qaytarish"""
    try:
        premium_profile = PremiumUser.objects.get(user=user)
        return premium_profile.can_add_premium()
    except PremiumUser.DoesNotExist:
        return False, "Premium profilingiz topilmadi"

def create_admin_notification(title, message, data=None):
    """Adminlarga bildirishnoma yaratish"""
    try:
        # Barcha adminlarga
        admin_users = User.objects.filter(
            Q(is_superuser=True) | Q(is_staff=True) | Q(groups__name='Admin')
        ).distinct()
        
        for admin in admin_users:
            PremiumNotification.objects.create(
                user=admin,
                notification_type='new_request',
                title=title,
                message=message,
                data=data or {}
            )
        return True
    except Exception as e:
        print(f"[create_admin_notification] Error: {e}")
        return False

def create_user_notification(user, notification_type, title, message, data=None):
    """Foydalanuvchiga bildirishnoma yaratish"""
    try:
        PremiumNotification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {}
        )
        return True
    except Exception as e:
        print(f"[create_user_notification] Error for {user.username}: {e}")
        return False

# ==================== CRON FUNCTIONS ====================

def check_and_update_premium_expiry():
    """Premium muddatini tekshirish va yangilash"""
    try:
        now = timezone.now()
        print(f"[CRON] Premium muddati tekshirilmoqda: {now}")
        
        result = {
            'expired_users': 0,
            'expired_products': 0,
            'expired_requests': 0,
            'renewed_users': 0,
            'notified_users': 0
        }
        
        # 1. PremiumUser muddati tugaganlarini tekshirish
        expired_premium_users = PremiumUser.objects.filter(
            is_premium=True,
            premium_end__lt=now
        )
        
        for premium_user in expired_premium_users:
            print(f"[CRON] Foydalanuvchi premium muddati tugadi: {premium_user.user.username}")
            
            if premium_user.deactivate_premium():
                result['expired_users'] += 1
        
        # 2. Premium mahsulotlar muddati tugaganlarini tekshirish
        expired_products = Mahsulot.objects.filter(
            is_premium=True,
            premium_expiry__lt=now
        )
        
        for product in expired_products:
            print(f"[CRON] Mahsulot premium muddati tugadi: {product.name}")
            
            product.deactivate_premium()
            product.is_premium = False
            product.save()
            result['expired_products'] += 1
        
        # 3. Premium so'rovlari muddati tugaganlarini tekshirish
        settings = AdminPremiumSettings.get_settings()
        expired_requests = PremiumRequest.objects.filter(
            status='pending',
            created_at__lte=now - timedelta(days=settings.premium_request_expiry_days)
        )
        
        for request in expired_requests:
            request.mark_as_expired()
            result['expired_requests'] += 1
        
        # 4. Premium tugashidan oldin ogohlantirish
        premium_users_to_notify = PremiumUser.objects.filter(
            is_premium=True,
            notified_before_expiry=False
        )
        
        for premium_user in premium_users_to_notify:
            if premium_user.should_notify_expiry():
                premium_user.notify_expiry()
                
                # Foydalanuvchiga bildirishnoma
                create_user_notification(
                    user=premium_user.user,
                    notification_type='expiry_soon',
                    title="Premium Muddati Tugash Arafasida",
                    message=f"Sizning premium obunangiz {premium_user.get_days_remaining()} kundan keyin tugaydi.",
                    data={'days_remaining': premium_user.get_days_remaining()}
                )
                result['notified_users'] += 1
        
        print(f"[CRON] Tekshirish yakunlandi: {result}")
        return result
        
    except Exception as e:
        print(f"[CRON] Xatolik: {e}")
        import traceback
        traceback.print_exc()
        return None

# ==================== ASOSIY SAHIFALAR ====================
from .models import AdminAloqa

def home_view(request):
    """Bosh sahifa"""
    try:
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()

        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
        device_type = 'mobile' if any(k in user_agent for k in mobile_keywords) else 'desktop'

        banners = Banner.objects.filter(
            device_type=device_type,
            is_active=True
        ).order_by('-created_at')[:5]

        premium_products = Mahsulot.objects.filter(
            is_premium=True,
            aktiv=True,
            sotilgan=False
        ).order_by('-premium_priority', '-premium_since')[:6]

        regular_products = Mahsulot.objects.filter(
            is_premium=False,
            aktiv=True,
            sotilgan=False
        ).order_by('-id')[:12]

        all_products = list(premium_products) + list(regular_products)

        # ⭐ MUHIM QOSHILDI
        admin_contact = AdminAloqa.objects.first()

        return render(request, 'home.html', {
            'mahsulotlar': all_products[:12],
            'banners': banners,
            'device_type': device_type,
            'premium_count': premium_products.count(),
            'regular_count': regular_products.count(),
            'admin_contact': admin_contact   # ⭐ SHU MUHIM
        })

    except Exception as e:
        print(e)
        return render(request, 'home.html', {})


def index(request):
    """Barcha mahsulotlar sahifasi"""
    try:
        # Premium mahsulotlar
        premium_products = Mahsulot.objects.filter(
            is_premium=True,
            aktiv=True,
            sotilgan=False
        ).order_by('-premium_priority', '-premium_since')
        
        # Oddiy mahsulotlar
        regular_products = Mahsulot.objects.filter(
            is_premium=False,
            aktiv=True,
            sotilgan=False
        ).order_by('-id')
        
        # Premium va oddiy mahsulotlarni birlashtirish
        all_products = list(premium_products) + list(regular_products)
        
        # Sahifalash
        paginator = Paginator(all_products, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'index.html', {
            'mahsulotlar': page_obj, 
            'page_obj': page_obj,
            'premium_count': premium_products.count(),
            'total_count': len(all_products)
        })
    except Exception as e:
        print(f"DEBUG: Xatolik - {e}")
        return render(request, 'index.html', {'mahsulotlar': []})

def barcha_mahsulotlar(request):
    q = request.GET.get('q', '').strip()
    filter_type = request.GET.get('filter', 'all')
    sort = request.GET.get('sort', 'premium')
    
    mahsulotlar = Mahsulot.objects.filter(aktiv=True, sotilgan=False)
    
    if q:
        from .search_service import SearchService
        mahsulotlar = SearchService.fuzzy_search(q)
    else:
        if filter_type == 'premium':
            mahsulotlar = mahsulotlar.filter(is_premium=True)
        elif filter_type == 'regular':
            mahsulotlar = mahsulotlar.filter(is_premium=False)
        
        # Saralash...
    
    paginator = Paginator(mahsulotlar, 24)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'barcha_mahsulotlar.html', {
        'mahsulotlar': page_obj,
        'page_obj': page_obj,
        'filter_type': filter_type,
        'sort': sort,
        'q': q,
    })
def kategoriya_view(request, category_name):
    """Kategoriyaga tegishli mahsulotlarni ko'rsatish"""
    try:
        # Modeldagi kategoriya nomlariga mapping
        category_map = {
            'elektronika': 'elektronika',
            'kitoblar': 'kitob',
            'mebellar': 'mebel',
            'chettovarlar': 'cheteltovarlar',
            'uy_joy': 'uyjoyelonlari',
            'onalar_va_bolalar': 'onavabollar',
            'uy_jihozlari': 'uy_jihozlari',
            'auto': 'avto_elonlari',
            'kiyim': 'kiyim',
            'avto': 'avto',
            'boshqa': 'boshqa',
        }
        
        # Modeldagi kategoriya nomlarini olish
        model_categories = dict(Mahsulot.CATEGORY_CHOICES)
        
        # Agar to'g'ridan-to'g'ri modeldagi kategoriya bo'lsa
        if category_name in model_categories:
            filtered_category = category_name
        else:
            # Mapperdan qidirish
            filtered_category = category_map.get(category_name, category_name)
        
        # Premium mahsulotlarni olish
        premium_products = Mahsulot.objects.filter(
            aktiv=True,
            is_premium=True,
            sotilgan=False,
            category=filtered_category
        ).order_by('-premium_priority', '-premium_since')
        
        # Oddiy mahsulotlarni olish
        regular_products = Mahsulot.objects.filter(
            aktiv=True,
            is_premium=False,
            sotilgan=False,
            category=filtered_category
        ).order_by('-sana')
        
        # Premium va oddiy mahsulotlarni birlashtirish
        mahsulotlar = list(premium_products) + list(regular_products)
        
        # Status filter
        status = request.GET.get('status', 'all')
        if status == 'new':
            mahsulotlar = [p for p in mahsulotlar if not p.sotilgan]
        elif status == 'sold':
            mahsulotlar = [p for p in mahsulotlar if p.sotilgan]
        
        # Saralash
        sort = request.GET.get('sort', 'premium')
        if sort == 'newest':
            mahsulotlar.sort(key=lambda x: x.sana, reverse=True)
        elif sort == 'oldest':
            mahsulotlar.sort(key=lambda x: x.sana)
        elif sort == 'price_low':
            mahsulotlar.sort(key=lambda x: float(str(x.narx).replace(',', '').replace(' ', '')) if str(x.narx).replace(',', '').replace(' ', '').replace('.', '').isdigit() else 0)
        elif sort == 'price_high':
            mahsulotlar.sort(key=lambda x: float(str(x.narx).replace(',', '').replace(' ', '')) if str(x.narx).replace(',', '').replace(' ', '').replace('.', '').isdigit() else 0, reverse=True)
        elif sort == 'premium':
            # Premiumlar birinchi, keyin oddiy mahsulotlar
            mahsulotlar = [p for p in mahsulotlar if p.is_premium] + [p for p in mahsulotlar if not p.is_premium]
        
        # Kategoriya nomi uchun ko'rinish
        category_display_names = {
            'elektronika': 'Elektronika',
            'kitob': 'Kitoblar',
            'mebel': 'Mebellar',
            'cheteltovarlar': 'Chet el tovarlari',
            'uyjoyelonlari': 'Uy joy elonlari',
            'onavabollar': 'Onalar va bolalar',
            'avto_elonlari': 'Auto elonlar',
            'uy_jihozlari': 'Uy jihozlari',
            'kiyim': 'Kiyim-kechak',
            'avto': 'Avto ehtiyot qismlar',
            'boshqa': 'Boshqa',
        }
        
        # Sahifalash
        paginator = Paginator(mahsulotlar, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'mahsulotlar': page_obj,
            'page_obj': page_obj,
            'category_name': category_display_names.get(filtered_category, filtered_category),
            'current_category': category_name,
            'total_count': len(mahsulotlar),
            'premium_count': premium_products.count(),
            'regular_count': regular_products.count(),
        }
        
        return render(request, 'kategoriya.html', context)
        
    except Exception as e:
        print(f"DEBUG kategoriya_view: Xatolik - {e}")
        messages.error(request, "Kategoriya topilmadi yoki xatolik yuz berdi.")
        return redirect('home')

def baner(request):
    """Bannerlarni ko'rsatadigan alohida sahifa"""
    try:
        # User agent ni tekshirish
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        # Qurilma turini aniqlash
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
        device_type = 'mobile' if any(keyword in user_agent for keyword in mobile_keywords) else 'desktop'
        
        # Device type bo'yicha bannerlarni olish
        banners = Banner.objects.filter(
            device_type=device_type,
            is_active=True
        ).order_by('-created_at')[:5]
        
        return render(request, 'baner.html', {
            'banners': banners,
            'device_type': device_type
        })
        
    except Exception as e:
        print(f"DEBUG baner: Xatolik - {e}")
        return render(request, 'baner.html', {
            'banners': [],
            'device_type': 'desktop'
        })

# ==================== MAHSULOT DETAIL VIEWLARI ====================

def mahsulot_detail_view(request, mahsulot_id):
    """Mahsulot tafsilotlari"""
    try:
        mahsulot = get_object_or_404(Mahsulot, id=mahsulot_id)

        if request.user.is_authenticated:
            mahsulot.korishlar_soni += 1
            mahsulot.save(update_fields=['korishlar_soni'])

        # Sevimlilarda borligini tekshirish
        in_favorites = False
        if request.user.is_authenticated:
            in_favorites = Sevimli.objects.filter(user=request.user, mahsulot=mahsulot).exists()

        # O'xshash mahsulotlar
        o_xshash = Mahsulot.objects.filter(
            category=mahsulot.category,
            aktiv=True,
            sotilgan=False
        ).exclude(id=mahsulot.id).order_by('-is_premium', '-premium_priority', '-sana')[:4]

        return render(request, 'mahsulot_detail.html', {
            'mahsulot': mahsulot,
            'o_xshash_mahsulotlar': o_xshash,
            'in_favorites': in_favorites,
            'is_premium': mahsulot.is_premium
        })

    except Mahsulot.DoesNotExist:
        messages.error(request, "Mahsulot topilmadi yoki o'chirilgan.")
        return redirect('index')
    except Exception as e:
        print(f"DEBUG: Xatolik - {e}")
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect('index')









def premium_product_detail_view(request, mahsulot_id):
    """Premium mahsulot tafsilotlari"""
    try:
        mahsulot = get_object_or_404(Mahsulot, id=mahsulot_id)
        
        # Premium mahsulot emas bo'lsa, oddiy detailga yo'naltirish
        if not mahsulot.is_premium:
            return redirect('mahsulot_detail', mahsulot_id=mahsulot.id)
        
        # Ko'rishlar sonini oshirish
        mahsulot.korishlar_soni += 1
        mahsulot.save(update_fields=['korishlar_soni'])
        
        # Sevimlilarda borligini tekshirish
        in_favorites = False
        if request.user.is_authenticated:
            in_favorites = Sevimli.objects.filter(
                user=request.user, 
                mahsulot=mahsulot
            ).exists()

        # O'xshash premium mahsulotlar
        o_xshash = Mahsulot.objects.filter(
            category=mahsulot.category,
            is_premium=True,
            aktiv=True,
            sotilgan=False
        ).exclude(id=mahsulot.id).order_by('-premium_priority', '-premium_since')[:8]

        # Seller profilini olish yoki yaratish
        seller_profile = None
        try:
            seller_profile = SellerProfile.objects.get(user=mahsulot.user)
        except SellerProfile.DoesNotExist:
            # Agar seller profile mavjud bo'lmasa, oddiy ma'lumotlar bilan ishlash
            seller_profile = {
                'user': mahsulot.user,
                'phone': mahsulot.telefon if hasattr(mahsulot, 'telefon') else '',
                'telegram': mahsulot.telegram_username if hasattr(mahsulot, 'telegram_username') else '',
                'location': f"{mahsulot.viloyat}, {mahsulot.tuman}" if hasattr(mahsulot, 'viloyat') and hasattr(mahsulot, 'tuman') else '',
            }
        
        # Mahsulotning barcha rasmlari
        images = []
        if mahsulot.asosiyimg:
            images.append(mahsulot.asosiyimg.url)
        if hasattr(mahsulot, 'birimg') and mahsulot.birimg:
            images.append(mahsulot.birimg.url)
        if hasattr(mahsulot, 'ikkiimg') and mahsulot.ikkiimg:
            images.append(mahsulot.ikkiimg.url)
        if hasattr(mahsulot, 'uchuimg') and mahsulot.uchuimg:
            images.append(mahsulot.uchuimg.url)

        context = {
            'mahsulot': mahsulot,
            'seller_profile': seller_profile,
            'o_xshash_mahsulotlar': o_xshash,
            'in_favorites': in_favorites,
            'is_premium': mahsulot.is_premium,
            'images': images,
            'title': f'{mahsulot.name} - Premium Mahsulot | Tez Sot',
            'meta_description': f'{mahsulot.name} - {mahsulot.narx_formatted()}. {mahsulot.tavsif[:150] if mahsulot.tavsif else ""}',
            'premium_time_left': mahsulot.get_premium_time_left() if hasattr(mahsulot, 'get_premium_time_left') else 0,
            'premium_status': mahsulot.get_premium_status_display() if hasattr(mahsulot, 'get_premium_status_display') else 'Premium',
        }
        
        return render(request, 'premium_product_detail.html', context)

    except Mahsulot.DoesNotExist:
        messages.error(request, "Premium mahsulot topilmadi yoki o'chirilgan.")
        return redirect('index')  # index sahifasiga yo'naltirish
    except Exception as e:
        print(f"DEBUG premium_product_detail: Xatolik - {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, "Noma'lum xatolik yuz berdi.")
        return redirect('mahsulot_detail', mahsulot_id=mahsulot_id)





def premium_products_view(request):
    """Premium mahsulotlar sahifasi"""
    try:
        # Premium mahsulotlarni olish
        premium_products = Mahsulot.objects.filter(
            is_premium=True,
            aktiv=True,
            sotilgan=False
        ).order_by('-premium_priority', '-premium_since', '-sana')
        
        # Userning premium statusini tekshirish
        is_premium_user = False
        if request.user.is_authenticated:
            try:
                premium_profile = PremiumUser.objects.get(user=request.user)
                is_premium_user = premium_profile.is_premium
            except PremiumUser.DoesNotExist:
                pass
        
        # Filter parametrlari
        q = request.GET.get('q', '')
        category = request.GET.get('category')
        viloyat = request.GET.get('viloyat')
        sort = request.GET.get('sort', 'premium')
        
        # Qidiruv filtri
        if q:
            premium_products = premium_products.filter(
                Q(name__icontains=q) | 
                Q(tavsif__icontains=q) |
                Q(category__icontains=q) |
                Q(mahsulotturi__icontains=q)
            )
        
        if category:
            premium_products = premium_products.filter(category=category)
        
        if viloyat:
            premium_products = premium_products.filter(viloyat=viloyat)
        
        # Saralash
        if sort == 'newest':
            premium_products = premium_products.order_by('-sana')
        elif sort == 'oldest':
            premium_products = premium_products.order_by('sana')
        elif sort == 'price_low':
            premium_products = premium_products.order_by('narx')
        elif sort == 'price_high':
            premium_products = premium_products.order_by('-narx')
        elif sort == 'views':
            premium_products = premium_products.order_by('-korishlar_soni')
        elif sort == 'premium':
            premium_products = premium_products.order_by('-premium_priority', '-premium_since')
        
        # Kategoriyalar ro'yxati
        categories = Mahsulot.objects.filter(
            is_premium=True,
            aktiv=True,
            sotilgan=False
        ).values_list('category', flat=True).distinct()
        
        # Statistikalar
        total_count = premium_products.count()
        
        # Sahifalash
        paginator = Paginator(premium_products, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'mahsulotlar': page_obj,
            'page_obj': page_obj,
            'is_premium_page': True,
            'total_count': total_count,
            'categories': categories,
            'sort': sort,
            'q': q,
            'category': category,
            'viloyat': viloyat,
            'user_authenticated': request.user.is_authenticated,
            'is_premium_user': is_premium_user,
            'title': 'Premium Mahsulotlar',
            'description': 'Eng sifatli va ishonchli premium mahsulotlar'
        }
        
        return render(request, 'premium_products.html', context)
        
    except Exception as e:
        print(f"DEBUG premium_products_view: Xatolik - {e}")
        messages.error(request, "Premium mahsulotlarni yuklashda xatolik yuz berdi.")
        return render(request, 'premium_products.html', {
            'mahsulotlar': [],
            'is_premium_page': True,
            'total_count': 0,
            'categories': [],
            'is_premium_user': False,
            'title': 'Premium Mahsulotlar'
        })



def admin_contact_view(request):
    """Admin bilan aloqa sahifasi"""
    settings = AdminPremiumSettings.get_settings()
    reason = request.GET.get('reason', 'Premium huquq yo\'q')
    
    return render(request, 'admin_contact.html',  {
        'admin_contact': settings,
        'reason': reason
    })


@login_required
def premium_product_check_view(request):
    """Premium mahsulot qo'shish uchun tekshirish"""
    try:
        premium_profile = PremiumUser.objects.get(user=request.user)
        
        # Premium sozlamalarni tekshirish
        settings = AdminPremiumSettings.get_settings()
        if not settings.is_premium_enabled:
            messages.error(request, "Premium tizim hozirda faol emas.")
            return redirect('elon_qoshish')
        
        # Premium huquqni tekshirish
        has_access, reason = check_premium_access(request.user)
        
        if has_access:
            # Qo'shish mumkin bo'lgan mahsulotlar sonini tekshirish
            can_add, add_reason = premium_profile.can_add_more_premium_products()
            if not can_add:
                messages.error(request, add_reason)
                return render(request, 'admin_contact.html', {
                    'admin_contact': settings,
                    'reason': add_reason
                })
            
            return redirect('add_premium_product')
        else:
            messages.warning(request, reason)
            return render(request, 'admin_contact.html', {
                'admin_contact': settings,
                'reason': reason
            })
            
    except PremiumUser.DoesNotExist:
        settings = AdminPremiumSettings.get_settings()
        messages.error(request, "Premium profilingiz topilmadi. Admin bilan bog'laning.")
        return render(request, 'admin_contact.html', {
            'admin_contact': settings,
            'reason': 'Premium profil yo\'q'
        })

@login_required
def add_premium_product_view(request):
    """Premium mahsulot qo'shish sahifasi"""
    try:
        # Premium sozlamalarni tekshirish
        settings = AdminPremiumSettings.get_settings()
        if not settings.is_premium_enabled:
            messages.error(request, "Premium tizim hozirda faol emas.")
            return redirect('elon_qoshish')
        
        # Premium profili ni olish
        premium_profile = PremiumUser.objects.get(user=request.user)
        
        # Premium huquqlarni tekshirish
        has_access, reason = check_premium_access(request.user)
        
        if not has_access:
            messages.error(request, reason)
            return render(request, 'admin_contact.html', {
                'admin_contact': settings,
                'reason': reason
            })
        
        # Qo'shish mumkin bo'lgan mahsulotlar sonini tekshirish
        can_add, add_reason = premium_profile.can_add_more_premium_products()
        if not can_add:
            messages.error(request, add_reason)
            return redirect('premium_product_check')
        
        if request.method == 'POST':
            try:
                # Form ma'lumotlarini olish
                category = request.POST.get('category')
                mahsulotturi = request.POST.get('mahsulotturi')
                name = request.POST.get('name')
                viloyat = request.POST.get('viloyat')
                narx_input = request.POST.get('narx', '0')
                asosiyimg = request.FILES.get('asosiyimg')

                # Majburiy maydonlarni tekshirish
                if not all([category, mahsulotturi, name, viloyat, narx_input, asosiyimg]):
                    messages.error(request, "Iltimos, barcha majburiy maydonlarni to'ldiring.")
                    return render(request, 'add_premium_product.html', {
                        'premium_profile': premium_profile,
                        'remaining': premium_profile.get_remaining_premium_products()
                    })

                # Narxni tozalash
                cleaned_narx = ''.join(c for c in narx_input if c.isdigit() or c in '.,') or '0'
                telefon = re.sub(r'\D', '', request.POST.get('telefon', ''))
                telegram_username = request.POST.get('telegram_username', '').lstrip('@')

                # Premium mahsulot yaratish
                mahsulot = Mahsulot.objects.create(
                    user=request.user,
                    category=category,
                    mahsulotturi=mahsulotturi,
                    name=name,
                    viloyat=viloyat,
                    tuman=request.POST.get('tuman', ''),
                    manzil=request.POST.get('manzil', ''),
                    telefon=telefon,
                    telegram_username=telegram_username,
                    email=request.POST.get('email', ''),
                    tavsif=request.POST.get('tavsif', ''),
                    narx=cleaned_narx,
                    asosiyimg=asosiyimg,
                    birimg=request.FILES.get('birimg'),
                    ikkiimg=request.FILES.get('ikkiimg'),
                    uchuimg=request.FILES.get('uchuimg'),
                    toltirish=request.FILES.get('toltirish'),
                    sana=timezone.now(),
                    sotilgan=False,
                    aktiv=True
                )

                # Premium qilish
                success, message = mahsulot.make_premium(
                    user=request.user,
                    auto_approve=settings.auto_approve_premium if hasattr(settings, 'auto_approve_premium') else False
                )
                
                if success:
                    messages.success(request, f'"{name}" premium mahsuloti muvaffaqiyatli qo\'shildi!')
                    return redirect('premium_product_detail', mahsulot_id=mahsulot.id)
                else:
                    messages.error(request, f'Premium qilishda xatolik: {message}')
                    mahsulot.delete()  # Mahsulotni o'chirish
                    return redirect('add_premium_product')

            except Exception as e:
                messages.error(request, f'Xatolik yuz berdi: {str(e)}')
        
        return render(request, 'add_premium_product.html', {
            'premium_profile': premium_profile,
            'remaining': premium_profile.get_remaining_premium_products(),
            'can_add': can_add,
            'add_reason': add_reason,
        })
        
    except PremiumUser.DoesNotExist:
        settings = AdminPremiumSettings.get_settings()
        messages.error(request, "Premium profilingiz topilmadi. Admin bilan bog'laning.")
        return render(request, 'admin_contact.html', {
            'admin_contact': settings
        })
    except Exception as e:
        messages.error(request, f'Xatolik yuz berdi: {str(e)}')
        return redirect('home')

# ==================== PREMIUM SO'ROV VIEWLARI ====================


@login_required
def my_premium_requests_view(request):
    """Foydalanuvchining premium so'rovlarini ko'rish"""
    try:
        # Foydalanuvchining so'rovlarini olish
        premium_requests = PremiumRequest.objects.filter(
            user=request.user
        ).order_by('-created_at')
        
        # So'rovlar sonini hisoblash
        pending_count = premium_requests.filter(status='pending').count()
        approved_count = premium_requests.filter(status='approved').count()
        rejected_count = premium_requests.filter(status='rejected').count()
        expired_count = premium_requests.filter(status='expired').count()
        
        # Premium profili
        try:
            premium_profile = PremiumUser.objects.get(user=request.user)
            has_premium = premium_profile.is_premium
            premium_info = {
                'is_premium': premium_profile.is_premium,
                'status': premium_profile.get_status_display(),
                'premium_end': premium_profile.premium_end.strftime('%d.%m.%Y') if premium_profile.premium_end else None,
                'days_remaining': premium_profile.get_days_remaining(),
                'limit': premium_profile.premium_limit,
                'used': premium_profile.premium_used,
            }
        except PremiumUser.DoesNotExist:
            has_premium = False
            premium_info = None
        
        # So'rovlar statistikasi
        stats = {
            'total': premium_requests.count(),
            'pending': pending_count,
            'approved': approved_count,
            'rejected': rejected_count,
            'expired': expired_count,
        }
        
        # So'rovlar limiti
        settings = AdminPremiumSettings.get_settings()
        requests_left = max(0, settings.max_premium_requests_per_user - pending_count - approved_count)
        
        context = {
            'premium_requests': premium_requests,
            'has_premium': has_premium,
            'premium_info': premium_info,
            'stats': stats,
            'requests_left': requests_left,
            'max_requests': settings.max_premium_requests_per_user,
            'title': 'Mening Premium So\'rovlarim',
        }
        
        return render(request, 'my_premium_requests.html', context)
        
    except Exception as e:
        print(f"My premium requests error: {str(e)}")
        messages.error(request, "So'rovlarni yuklashda xatolik yuz berdi")
        return redirect('my_profile')

@login_required
def cancel_premium_request_view(request, request_id):
    """Premium so'rovni bekor qilish"""
    try:
        # So'rovni topish
        premium_request = PremiumRequest.objects.get(
            id=request_id,
            user=request.user
        )
        
        # Faqat pending holatdagilarni bekor qilish mumkin
        if premium_request.status != 'pending':
            messages.error(request, "Faqat kutilayotgan so'rovlarni bekor qilish mumkin")
            return redirect('my_premium_requests')
        
        # So'rovni o'chirish
        premium_request.delete()
        
        messages.success(request, "So'rovingiz muvaffaqiyatli bekor qilindi")
        
    except PremiumRequest.DoesNotExist:
        messages.error(request, "So'rov topilmadi")
    except Exception as e:
        print(f"Cancel premium request error: {str(e)}")
        messages.error(request, f"So'rovni bekor qilishda xatolik: {str(e)}")
    
    return redirect('my_premium_requests')

@login_required
def premium_request_detail_view(request, request_id):
    """Premium so'rov tafsilotlari"""
    try:
        # So'rovni topish
        premium_request = get_object_or_404(
            PremiumRequest,
            id=request_id,
            user=request.user
        )
        
        # So'rov ma'lumotlarini formatlash
        request_info = {
            'id': premium_request.id,
            'full_name': premium_request.full_name,
            'phone': premium_request.phone,
            'telegram': f"@{premium_request.telegram_username}" if premium_request.telegram_username else "Ko'rsatilmagan",
            'email': premium_request.email or "Ko'rsatilmagan",
            'days': premium_request.requested_days,
            'limit': premium_request.requested_limit,
            'total': f"{premium_request.calculated_total:,.0f}".replace(',', ' ') if premium_request.calculated_total else "0",
            'status': premium_request.get_status_display(),
            'status_color': {
                'pending': 'warning',
                'approved': 'success',
                'rejected': 'danger',
                'expired': 'secondary'
            }.get(premium_request.status, 'secondary'),
            'created_at': premium_request.created_at.strftime('%d.%m.%Y %H:%M'),
            'updated_at': premium_request.updated_at.strftime('%d.%m.%Y %H:%M') if premium_request.updated_at else None,
            'admin_notes': premium_request.admin_notes,
            'notes': premium_request.notes,
        }
        
        # Admin aloqa ma'lumotlari
        settings = AdminPremiumSettings.get_settings()
        
        context = {
            'request': request_info,
            'premium_request': premium_request,
            'admin_contact': {
                'phone': settings.admin_contact_phone,
                'telegram': settings.admin_contact_telegram,
                'email': settings.admin_contact_email,
            },
            'title': f'Premium So\'rov #{premium_request.id}',
        }
        
        return render(request, 'premium_request_detail.html', context)
        
    except PremiumRequest.DoesNotExist:
        messages.error(request, "So'rov topilmadi")
        return redirect('my_premium_requests')
    except Exception as e:
        print(f"Premium request detail error: {str(e)}")
        messages.error(request, "So'rovni yuklashda xatolik yuz berdi")
        return redirect('my_premium_requests')

# views.py - check_premium_status_view


def get_status_color(status):
    """Status rangini aniqlash"""
    colors = {
        'active': 'success',
        'approved': 'success',
        'pending': 'warning',
        'rejected': 'danger',
        'expired': 'secondary',
        'cancelled': 'dark',
        'no_premium': 'secondary',
    }
    return colors.get(status, 'secondary')
# ==================== E'LON QO'SHISH VIEWLARI ====================

@login_required
def elon_qoshish_view(request):
    """Yangi e'lon qo'shish (oddiy)"""
    if request.method == 'POST':
        try:
            category = request.POST.get('category')
            mahsulotturi = request.POST.get('mahsulotturi')
            name = request.POST.get('name')
            viloyat = request.POST.get('viloyat')
            narx_input = request.POST.get('narx', '0')
            asosiyimg = request.FILES.get('asosiyimg')

            if not all([category, mahsulotturi, name, viloyat, narx_input, asosiyimg]):
                messages.error(request, "Iltimos, barcha majburiy maydonlarni to'ldiring.")
                return render(request, 'elon_qoshish.html')

            cleaned_narx = ''.join(c for c in narx_input if c.isdigit() or c in '.,') or '0'
            telefon = re.sub(r'\D', '', request.POST.get('telefon', ''))
            telegram_username = request.POST.get('telegram_username', '').lstrip('@')

            mahsulot = Mahsulot.objects.create(
                user=request.user,
                category=category,
                mahsulotturi=mahsulotturi,
                name=name,
                viloyat=viloyat,
                tuman=request.POST.get('tuman', ''),
                manzil=request.POST.get('manzil', ''),
                telefon=telefon,
                telegram_username=telegram_username,
                email=request.POST.get('email', ''),
                tavsif=request.POST.get('tavsif', ''),
                narx=cleaned_narx,
                asosiyimg=asosiyimg,
                birimg=request.FILES.get('birimg'),
                ikkiimg=request.FILES.get('ikkiimg'),
                uchuimg=request.FILES.get('uchuimg'),
                toltirish=request.FILES.get('toltirish'),
                sana=timezone.now(),
                sotilgan=False,
                aktiv=True
            )

            messages.success(request, f'"{name}" mahsuloti muvaffaqiyatli qo\'shildi!')
            return redirect('mahsulot_detail', mahsulot_id=mahsulot.id)

        except Exception as e:
            messages.error(request, f'Xatolik yuz berdi: {str(e)}')

    return render(request, 'elon_qoshish.html')

# ==================== PROFIL VIEWLARI ====================

@login_required
def settings_view(request):
    """Sozlamalar sahifasini ko'rsatish"""
    user = request.user
    
    # SellerProfile ni majburiy yaratish
    seller_profile, created = SellerProfile.objects.get_or_create(user=user)
    
    # Premium profil
    premium_profile = None
    try:
        premium_profile = PremiumUser.objects.get(user=user)
    except PremiumUser.DoesNotExist:
        pass
    
    # Premium so'rovlar
    premium_requests = PremiumRequest.objects.filter(user=user).order_by('-created_at')[:5]
    
    context = {
        'user': user,
        'seller_profile': seller_profile,
        'premium_profile': premium_profile,
        'premium_requests': premium_requests,
    }
    return render(request, 'sozlamalar.html', context)

@login_required
def update_profile_settings(request):
    """Profil ma'lumotlarini yangilash"""
    if request.method == 'POST':
        try:
            user = request.user
            
            # 1. User asosiy ma'lumotlari
            user.first_name = request.POST.get('firstName', user.first_name)
            user.last_name = request.POST.get('lastName', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.save()
            
            # 2. SellerProfile ni yangilash
            try:
                seller_profile = SellerProfile.objects.get(user=user)
                
                seller_phone = request.POST.get('phone', '')
                if seller_phone:
                    seller_profile.phone = seller_phone
                
                seller_profile.telegram = request.POST.get('telegram', seller_profile.telegram)
                seller_profile.instagram = request.POST.get('instagram', seller_profile.instagram)
                seller_profile.location = request.POST.get('location', seller_profile.location)
                seller_profile.bio = request.POST.get('bio', seller_profile.bio)
                
                if 'profile_image' in request.FILES:
                    seller_profile.profile_image = request.FILES['profile_image']
                
                seller_profile.save()
                
            except Exception as e:
                print(f"DEBUG: Seller Profile error: {e}")
            
            # JSON response
            response_data = {
                'status': 'success',
                'message': 'Profil ma\'lumotlari muvaffaqiyatli yangilandi!'
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            print(f"DEBUG ERROR: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Xatolik yuz berdi: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Noto\'g\'ri so\'rov'})

@login_required
def update_password(request):
    """Parolni yangilash"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Parol muvaffaqiyatli yangilandi!'})
            messages.success(request, 'Parolingiz muvaffaqiyatli yangilandi!')
        else:
            errors = list(form.errors.values())[0] if form.errors else []
            error_msg = errors[0] if errors else 'Parolni yangilashda xatolik yuz berdi'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg})
            messages.error(request, error_msg)
    
    return redirect('sozlamalar')

@login_required
@csrf_exempt
def update_notifications(request):
    """Bildirishnoma sozlamalarini yangilash"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            return JsonResponse({'status': 'success', 'message': 'Sozlamalar saqlandi!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Noto\'g\'ri so\'rov'})

# ==================== Mening e'lonlarim VIEWLARI ====================

@login_required
def mening_elonlarim_view(request):
    """Foydalanuvchining o'z e'lonlari"""
    try:
        status = request.GET.get('status')
        mahsulotlar = Mahsulot.objects.filter(user=request.user).order_by('-id')

        if status == 'yangi':
            mahsulotlar = mahsulotlar.filter(sotilgan=False)
        elif status == 'sotilgan':
            mahsulotlar = mahsulotlar.filter(sotilgan=True)
        elif status == 'premium':
            mahsulotlar = mahsulotlar.filter(is_premium=True)
        elif status == 'regular':
            mahsulotlar = mahsulotlar.filter(is_premium=False)

        paginator = Paginator(mahsulotlar, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Statistikalar
        total_count = mahsulotlar.count()
        active_count = mahsulotlar.filter(sotilgan=False).count()
        sold_count = mahsulotlar.filter(sotilgan=True).count()
        premium_count = mahsulotlar.filter(is_premium=True).count()
        
        # Premium profil
        premium_profile = None
        try:
            premium_profile = PremiumUser.objects.get(user=request.user)
        except PremiumUser.DoesNotExist:
            pass

        return render(request, 'mening_elonlarim.html', {
            'mahsulotlar': page_obj, 
            'page_obj': page_obj,
            'status': status,
            'total_count': total_count,
            'active_count': active_count,
            'sold_count': sold_count,
            'premium_count': premium_count,
            'premium_profile': premium_profile,
            'mahsulot_list': mahsulotlar.filter(sotilgan=False)
        })
    except Exception as e:
        print(f"DEBUG: Xatolik - {e}")
        return render(request, 'mening_elonlarim.html', {'mahsulotlar': []})

@login_required
def sotilgan_qilish_view(request, mahsulot_id):
    """Mahsulotni sotilgan qilish"""
    try:
        mahsulot = get_object_or_404(Mahsulot, id=mahsulot_id, user=request.user)
        
        if mahsulot.sotilgan:
            messages.warning(request, f'"{mahsulot.name}" allaqachon sotilgan!')
        else:
            mahsulot.sotilgan = True
            mahsulot.save()
            messages.success(request, f'"{mahsulot.name}" sotilganlar ro\'yxatiga o\'tkazildi!')
        
        status = request.POST.get('status', request.GET.get('status', ''))
        
        if status:
            return redirect(f'{reverse("mening_elonlarim")}?status={status}')
        return redirect('mening_elonlarim')
        
    except Mahsulot.DoesNotExist:
        messages.error(request, "Mahsulot topilmadi")
        return redirect('mening_elonlarim')
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {str(e)}")
        return redirect('mening_elonlarim')

@login_required
def yangi_qilish_view(request, mahsulot_id):
    """Mahsulotni yangi qilish (sotilmagan qilish)"""
    try:
        mahsulot = get_object_or_404(Mahsulot, id=mahsulot_id, user=request.user)
        
        if not mahsulot.sotilgan:
            messages.warning(request, f'"{mahsulot.name}" allaqachon yangi holatda!')
        else:
            mahsulot.sotilgan = False
            mahsulot.save()
            messages.success(request, f'"{mahsulot.name}" yangi mahsulotlar ro\'yxatiga qo\'shildi!')
        
        status = request.POST.get('status', request.GET.get('status', ''))
        
        if status:
            return redirect(f'{reverse("mening_elonlarim")}?status={status}')
        return redirect('mening_elonlarim')
        
    except Mahsulot.DoesNotExist:
        messages.error(request, "Mahsulot topilmadi")
        return redirect('mening_elonlarim')
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {str(e)}")
        return redirect('mening_elonlarim')

@login_required
def elon_ochirish_view(request, mahsulot_id):
    """E'lonni o'chirish"""
    if request.method == 'POST':
        try:
            mahsulot = Mahsulot.objects.get(id=mahsulot_id, user=request.user)
            
            # Agar premium mahsulot bo'lsa, premium counter ni kamaytirish
            if mahsulot.is_premium:
                try:
                    premium_profile = PremiumUser.objects.get(user=request.user)
                    premium_profile.premium_used = Mahsulot.objects.filter(
                        user=request.user,
                        is_premium=True,
                        premium_expiry__gt=timezone.now()
                    ).exclude(id=mahsulot_id).count()
                    premium_profile.save(update_fields=['premium_used'])
                except PremiumUser.DoesNotExist:
                    pass
            
            mahsulot.delete()
            messages.success(request, "E'lon muvaffaqiyatli o'chirildi!")
        except Mahsulot.DoesNotExist:
            messages.error(request, "E'lon topilmadi yoki sizga tegishli emas!")
        except Exception as e:
            messages.error(request, f"Xatolik yuz berdi: {str(e)}")
    
    status = request.POST.get('status', request.GET.get('status', None))
    
    if status:
        return redirect(f'{reverse("mening_elonlarim")}?status={status}')
    return redirect('mening_elonlarim')

# ==================== ADMIN PREMIUM VIEWLARI ====================

@login_required
@user_passes_test(is_admin)
def admin_premium_dashboard(request):
    """Admin premium boshqaruv paneli"""
    try:
        # Premium so'rovlari
        premium_requests = PremiumRequest.objects.filter(
            status='pending'
        ).order_by('-created_at')[:10]
        
        # Premium foydalanuvchilar
        premium_users = PremiumUser.objects.filter(is_premium=True).order_by('-premium_since')[:10]
        
        # Premium mahsulotlar
        premium_products = PremiumProduct.objects.all().order_by('-premium_since')[:10]
        
        # Premium sozlamalar
        settings = AdminPremiumSettings.get_settings()
        
        # Statistikalar
        stats = {
            'total_premium_users': PremiumUser.objects.filter(is_premium=True).count(),
            'pending_requests': PremiumRequest.objects.filter(status='pending').count(),
            'total_premium_products': PremiumProduct.objects.count(),
            'active_premium_products': PremiumProduct.objects.filter(is_active=True).count(),
            'expired_soon': PremiumUser.objects.filter(
                is_premium=True,
                premium_end__lte=timezone.now() + timedelta(days=3),
                premium_end__gt=timezone.now()
            ).count(),
            'expired_users': PremiumUser.objects.filter(
                is_premium=False,
                status='expired'
            ).count(),
            'today_requests': PremiumRequest.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
        }
        
        return render(request, 'admin/premium_dashboard.html', {
            'premium_requests': premium_requests,
            'premium_users': premium_users,
            'premium_products': premium_products,
            'settings': settings,
            'stats': stats
        })
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {str(e)}")
        return redirect('admin:index')

@login_required
@user_passes_test(is_admin)
def admin_premium_requests_view(request):
    """Admin uchun barcha premium so'rovlari"""
    try:
        # Filterlar
        status = request.GET.get('status', 'pending')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        search = request.GET.get('search', '')
        
        # So'rovlarni olish
        premium_requests = PremiumRequest.objects.all().order_by('-created_at')
        
        # Filter qo'llash
        if status != 'all':
            premium_requests = premium_requests.filter(status=status)
        
        if date_from:
            try:
                from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d')
                premium_requests = premium_requests.filter(created_at__gte=from_date)
            except:
                pass
        
        if date_to:
            try:
                to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d')
                premium_requests = premium_requests.filter(created_at__lte=to_date)
            except:
                pass
        
        if search:
            premium_requests = premium_requests.filter(
                Q(user__username__icontains=search) |
                Q(full_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Statistikalar
        stats = {
            'total': PremiumRequest.objects.count(),
            'pending': PremiumRequest.objects.filter(status='pending').count(),
            'approved': PremiumRequest.objects.filter(status='approved').count(),
            'rejected': PremiumRequest.objects.filter(status='rejected').count(),
            'expired': PremiumRequest.objects.filter(status='expired').count(),
            'today': PremiumRequest.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
        }
        
        # Sahifalash
        paginator = Paginator(premium_requests, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'premium_requests': page_obj,
            'page_obj': page_obj,
            'stats': stats,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
        
        return render(request, 'admin/premium_requests.html', context)
        
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {str(e)}")
        return redirect('admin_premium_dashboard')

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_process_premium_request(request, request_id):
    """Premium so'rovni qayta ishlash"""
    try:
        premium_request = PremiumRequest.objects.get(id=request_id)
        action = request.POST.get('action')
        
        if action == 'approve':
            days = int(request.POST.get('days', premium_request.requested_days))
            limit = int(request.POST.get('limit', premium_request.requested_limit))
            admin_notes = request.POST.get('admin_notes', '')
            
            # Premium so'rovni tasdiqlash
            success = premium_request.approve(request.user, days, limit)
            
            if success:
                messages.success(request, f"Premium so'rov tasdiqlandi. Foydalanuvchi {days} kun va {limit} limit bilan premium bo'ldi.")
            else:
                messages.error(request, "Premium so'rovni tasdiqlashda xatolik yuz berdi")
            
        elif action == 'reject':
            reason = request.POST.get('reason', '')
            premium_request.reject(request.user, reason)
            
            messages.success(request, "Premium so'rov rad etildi")
        
        elif action == 'delete':
            premium_request.delete()
            messages.success(request, "Premium so'rov o'chirildi")
        
        elif action == 'mark_expired':
            premium_request.mark_as_expired()
            messages.success(request, "Premium so'rov muddati o'tgan deb belgilandi")
        
    except PremiumRequest.DoesNotExist:
        messages.error(request, "So'rov topilmadi")
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {str(e)}")
    
    return redirect('admin_premium_requests')

@login_required
@user_passes_test(is_admin)
def admin_search_users_view(request):
    """Admin uchun foydalanuvchilarni qidirish"""
    try:
        search_query = request.GET.get('q', '').strip()
        search_type = request.GET.get('type', 'all')  # all, phone, username, name
        
        users = User.objects.all()
        
        if search_query:
            if search_type == 'phone':
                # Telefon raqami bo'yicha qidirish
                users = users.filter(
                    Q(seller_profile__phone__icontains=search_query) |
                    Q(premium_requests__phone__icontains=search_query)
                ).distinct()
            elif search_type == 'username':
                # Username bo'yicha qidirish
                users = users.filter(username__icontains=search_query)
            elif search_type == 'name':
                # Ism-familiya bo'yicha qidirish
                users = users.filter(
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(premium_requests__full_name__icontains=search_query)
                ).distinct()
            else:
                # Barcha maydonlar bo'yicha qidirish
                users = users.filter(
                    Q(username__icontains=search_query) |
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(email__icontains=search_query) |
                    Q(seller_profile__phone__icontains=search_query) |
                    Q(premium_requests__phone__icontains=search_query) |
                    Q(premium_requests__full_name__icontains=search_query)
                ).distinct()
        
        # Premium ma'lumotlarni qo'shish
        users_with_premium = []
        for user in users[:50]:  # 50 ta natijani cheklaymiz
            try:
                premium_profile = PremiumUser.objects.get(user=user)
                premium_status = premium_profile.get_status_display()
                is_premium = premium_profile.is_premium
                premium_requests_count = PremiumRequest.objects.filter(user=user).count()
            except PremiumUser.DoesNotExist:
                premium_status = "Premium yo'q"
                is_premium = False
                premium_requests_count = 0
            
            try:
                phone = user.seller_profile.phone if hasattr(user, 'seller_profile') and user.seller_profile.phone else ''
            except:
                phone = ''
            
            users_with_premium.append({
                'user': user,
                'phone': phone,
                'premium_status': premium_status,
                'is_premium': is_premium,
                'premium_requests_count': premium_requests_count,
                'has_premium_profile': PremiumUser.objects.filter(user=user).exists()
            })
        
        context = {
            'users': users_with_premium,
            'search_query': search_query,
            'search_type': search_type,
            'total_results': len(users_with_premium),
        }
        
        return render(request, 'admin/search_users.html', context)
        
    except Exception as e:
        messages.error(request, f"Qidiruvda xatolik: {str(e)}")
        return redirect('admin_premium_dashboard')

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_extend_premium(request, user_id):
    """Premium muddatini uzaytirish"""
    try:
        premium_user = PremiumUser.objects.get(user_id=user_id)
        
        if not premium_user.is_premium:
            messages.error(request, "Bu foydalanuvchi premium emas.")
            return redirect('admin_premium_dashboard')
        
        days = int(request.POST.get('days', 30))
        notes = request.POST.get('notes', '')
        
        # Premium muddatini uzaytirish
        if premium_user.premium_end:
            new_end = premium_user.premium_end + timedelta(days=days)
        else:
            new_end = timezone.now() + timedelta(days=days)
        
        premium_user.premium_end = new_end
        premium_user.premium_days += days
        
        if notes:
            premium_user.admin_notes = f"{premium_user.admin_notes or ''}\nUzaytirildi: {notes}"
        
        premium_user.save()
        
        # Mahsulotlarning premium muddatini ham uzaytirish
        premium_products = Mahsulot.objects.filter(
            user=premium_user.user,
            is_premium=True
        )
        
        for product in premium_products:
            if product.premium_expiry:
                product.premium_expiry = product.premium_expiry + timedelta(days=days)
                product.premium_days += days
                product.save()
        
        messages.success(request, f"{premium_user.user.username} premium muddati {days} kunga uzaytirildi!")
        
    except PremiumUser.DoesNotExist:
        messages.error(request, "Premium foydalanuvchi topilmadi")
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {str(e)}")
    
    return redirect('admin_premium_dashboard')

@login_required
@user_passes_test(is_admin)
def admin_check_all_expired(request):
    """Barcha premium muddati o'tgan foydalanuvchilarni tekshirish"""
    try:
        result = check_and_update_premium_expiry()
        
        if result:
            messages.success(request, 
                f"Tekshirish yakunlandi: {result['expired_users']} foydalanuvchi, "
                f"{result['expired_products']} mahsulot, "
                f"{result['expired_requests']} so'rov deaktivlashtirildi, "
                f"{result['notified_users']} foydalanuvchi ogohlantirildi")
        else:
            messages.error(request, "Tekshirishda xatolik yuz berdi")
        
    except Exception as e:
        messages.error(request, f"Tekshirishda xatolik: {str(e)}")
    
    return redirect('admin_premium_dashboard')

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_reset_premium_counter(request, user_id):
    """Premium counter ni qayta hisoblash"""
    try:
        premium_user = PremiumUser.objects.get(user_id=user_id)
        new_count = premium_user.reset_premium_counter()
        
        messages.success(request, f"Premium counter yangilandi. Yangi qiymat: {new_count}")
        
    except PremiumUser.DoesNotExist:
        messages.error(request, "Premium foydalanuvchi topilmadi")
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {str(e)}")
    
    return redirect('admin_premium_dashboard')

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_reactivate_premium(request, user_id):
    """Muddati tugagan premiumni qayta faollashtirish"""
    try:
        premium_user = PremiumUser.objects.get(user_id=user_id)
        
        days = int(request.POST.get('days', 30))
        reactivate_products = request.POST.get('reactivate_products') == 'on'
        notes = request.POST.get('notes', '')
        
        # Premiumni qayta faollashtirish
        success = premium_user.activate_premium(days=days, admin_user=request.user)
        
        if success:
            if reactivate_products:
                # Eski premium mahsulotlarni qayta premium qilish
                old_premium_products = Mahsulot.objects.filter(
                    user=premium_user.user,
                    aktiv=True,
                    sotilgan=False,
                    is_premium=False
                )
                
                for product in old_premium_products:
                    product.make_premium(
                        user=premium_user.user,
                        days=days,
                        auto_approve=True
                    )
            
            messages.success(request, f"{premium_user.user.username} premium qayta faollashtirildi!")
        else:
            messages.error(request, f"{premium_user.user.username} premium faollashtirishda xatolik!")
        
    except PremiumUser.DoesNotExist:
        messages.error(request, "Foydalanuvchi topilmadi")
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {str(e)}")
    
    return redirect('admin_premium_dashboard')

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_set_premium_limit(request, user_id):
    """Premium foydalanuvchi limitini o'zgartirish"""
    try:
        premium_user = PremiumUser.objects.get(user_id=user_id)
        new_limit = int(request.POST.get('limit', 5))
        
        premium_user.premium_limit = new_limit
        premium_user.save()
        
        messages.success(request, f"{premium_user.user.username} limiti {new_limit} ga o'zgartirildi!")
        
    except PremiumUser.DoesNotExist:
        messages.error(request, "Premium foydalanuvchi topilmadi")
    
    return redirect('admin_premium_dashboard')

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_toggle_premium_product(request, product_id):
    """Premium mahsulotni aktiv/inaktiv qilish"""
    try:
        premium_product = PremiumProduct.objects.get(id=product_id)
        action = request.POST.get('action')
        
        if action == 'activate':
            premium_product.is_active = True
            premium_product.mahsulot.aktiv = True
            messages.success(request, "Mahsulot aktivlashtirildi!")
        elif action == 'deactivate':
            premium_product.is_active = False
            premium_product.mahsulot.aktiv = False
            messages.success(request, "Mahsulot deaktivlashtirildi!")
        elif action == 'approve':
            premium_product.approve_premium(request.user)
            messages.success(request, "Mahsulot premium sifatida tasdiqlandi!")
        elif action == 'remove_premium':
            premium_product.mark_as_regular()
            messages.success(request, "Mahsulot premiumdan olib tashlandi!")
        
        premium_product.save()
        premium_product.mahsulot.save()
        
    except (PremiumProduct.DoesNotExist, Mahsulot.DoesNotExist):
        messages.error(request, "Mahsulot topilmadi")
    
    return redirect('admin_premium_dashboard')

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_update_premium_settings(request):
    """Premium sozlamalarni yangilash"""
    try:
        settings = AdminPremiumSettings.get_settings()
        
        # Asosiy sozlamalar
        settings.max_premium_products = int(request.POST.get('max_premium_products', 10))
        settings.premium_duration_days = int(request.POST.get('premium_duration_days', 30))
        settings.is_premium_enabled = request.POST.get('is_premium_enabled') == 'on'
        
        # Aloqa ma'lumotlari
        settings.admin_contact_phone = request.POST.get('admin_contact_phone', '')
        settings.admin_contact_telegram = request.POST.get('admin_contact_telegram', '')
        settings.admin_contact_email = request.POST.get('admin_contact_email', '')
        
        # To'lov va tasdiq
        settings.premium_fee_amount = float(request.POST.get('premium_fee_amount', 50000))
        settings.require_admin_approval = request.POST.get('require_admin_approval') == 'on'
        settings.auto_approve_premium = request.POST.get('auto_approve_premium') == 'on'
        
        # Design
        settings.premium_badge_color = request.POST.get('premium_badge_color', '#FFD700')
        
        # Premium cheklovlari
        settings.can_reactivate_old = request.POST.get('can_reactivate_old') == 'on'
        settings.check_expiry_every_hours = int(request.POST.get('check_expiry_every_hours', 1))
        settings.notify_before_days = int(request.POST.get('notify_before_days', 3))
        
        # So'rov sozlamalari
        settings.premium_request_expiry_days = int(request.POST.get('premium_request_expiry_days', 7))
        settings.auto_check_expiry = request.POST.get('auto_check_expiry') == 'on'
        settings.send_notifications = request.POST.get('send_notifications') == 'on'
        settings.max_premium_requests_per_user = int(request.POST.get('max_premium_requests_per_user', 3))
        
        settings.save()
        
        messages.success(request, "Premium sozlamalar yangilandi!")
        
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {str(e)}")
    
    return redirect('admin_premium_dashboard')

# ==================== API VIEWLARI ====================

def api_search(request):
    """Real-time qidiruv API"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    try:
        # Mahsulotlarni qidirish
        mahsulotlar = Mahsulot.objects.filter(
            Q(name__icontains=query) | 
            Q(tavsif__icontains=query) |
            Q(category__icontains=query) |
            Q(mahsulotturi__icontains=query),
            aktiv=True,
            sotilgan=False
        ).order_by('-is_premium', '-premium_priority', '-sana')[:10]
        
        results = []
        for product in mahsulotlar:
            results.append({
                'id': product.id,
                'name': product.name,
                'price': product.narx_formatted(),
                'category': product.get_category_display(),
                'image': product.asosiyimg.url if product.asosiyimg else None,
                'url': f"/mahsulot/{product.id}/",
                'is_premium': product.is_premium,
                'premium_badge': product.get_premium_badge() if product.is_premium else ''
            })
        
        return JsonResponse(results, safe=False)
    except Exception as e:
        print(f"DEBUG api_search xatolik: {e}")
        return JsonResponse([], safe=False)

@login_required
@require_GET
def get_premium_status(request):
    """Premium holatini olish (AJAX)"""
    try:
        premium_profile = PremiumUser.objects.get(user=request.user)
        
        # Premium so'rovlar soni
        pending_requests = PremiumRequest.objects.filter(
            user=request.user,
            status='pending'
        ).count()
        
        data = {
            'is_premium': premium_profile.is_premium,
            'status': premium_profile.get_status_display(),
            'days_remaining': premium_profile.get_days_remaining(),
            'premium_start': premium_profile.premium_start.strftime('%Y-%m-%d') if premium_profile.premium_start else None,
            'premium_end': premium_profile.premium_end.strftime('%Y-%m-%d') if premium_profile.premium_end else None,
            'premium_used': premium_profile.premium_used,
            'premium_limit': premium_profile.premium_limit,
            'remaining_products': premium_profile.get_remaining_premium_products(),
            'can_add_premium': premium_profile.can_add_premium()[0],
            'pending_requests': pending_requests,
        }
        
        return JsonResponse({'success': True, 'data': data})
        
    except PremiumUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Premium profil topilmadi'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_POST
def make_product_premium(request, product_id):
    """Mahsulotni premium qilish (AJAX)"""
    try:
        mahsulot = get_object_or_404(Mahsulot, id=product_id, user=request.user)
        
        # Premium huquqni tekshirish
        premium_profile = PremiumUser.objects.get(user=request.user)
        can_add, reason = premium_profile.can_add_premium()
        
        if not can_add:
            return JsonResponse({
                'success': False,
                'error': reason
            })
        
        # Qo'shish mumkin bo'lgan mahsulotlar sonini tekshirish
        can_add_more, add_reason = premium_profile.can_add_more_premium_products()
        if not can_add_more:
            return JsonResponse({
                'success': False,
                'error': add_reason
            })
        
        # Premium qilish
        settings = AdminPremiumSettings.get_settings()
        success, message = mahsulot.make_premium(
            user=request.user,
            auto_approve=settings.auto_approve_premium if hasattr(settings, 'auto_approve_premium') else False
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'product_id': mahsulot.id,
                'is_premium': mahsulot.is_premium,
                'premium_expiry': mahsulot.premium_expiry.strftime('%Y-%m-%d') if mahsulot.premium_expiry else None,
                'premium_used': premium_profile.premium_used,
                'premium_limit': premium_profile.premium_limit,
                'remaining': premium_profile.get_remaining_premium_products()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': message
            })
            
    except Mahsulot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mahsulot topilmadi'})
    except PremiumUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Premium profil topilmadi'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_POST
def remove_product_premium(request, product_id):
    """Mahsulotni premiumdan olib tashlash (AJAX)"""
    try:
        mahsulot = get_object_or_404(Mahsulot, id=product_id, user=request.user)
        
        if not mahsulot.is_premium:
            return JsonResponse({
                'success': False,
                'error': 'Mahsulot allaqachon premium emas'
            })
        
        mahsulot.remove_premium()
        
        # Counter yangilash
        try:
            premium_profile = PremiumUser.objects.get(user=request.user)
            premium_profile.reset_premium_counter()
        except PremiumUser.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': True,
            'message': 'Mahsulot premiumdan olib tashlandi',
            'product_id': mahsulot.id,
            'is_premium': mahsulot.is_premium
        })
            
    except Mahsulot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mahsulot topilmadi'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ==================== SEVIMLILAR VIEWLARI ====================

@login_required
def sevimliga_qoshish_view(request, mahsulot_id):
    """Mahsulotni sevimlilarga qo'shish"""
    try:
        mahsulot = get_object_or_404(Mahsulot, id=mahsulot_id)
        sevimli, created = Sevimli.objects.get_or_create(user=request.user, mahsulot=mahsulot)

        if created:
            messages.success(request, f'"{mahsulot.name}" sevimlilarga qo\'shildi ❤️')
        else:
            messages.info(request, f'"{mahsulot.name}" allaqachon sevimlilarda bor.')

        return redirect(request.META.get('HTTP_REFERER', 'home'))

    except Exception as e:
        messages.error(request, f'Xatolik yuz berdi: {str(e)}')
        return redirect('home')

@login_required
def sevimlilarim_view(request):
    """Foydalanuvchining sevimlilari"""
    try:
        filter_type = request.GET.get('filter', 'all')
        
        # Barcha sevimlilarni olish
        sevimlilar = Sevimli.objects.filter(user=request.user).order_by('-sana')
        
        # Filter qo'llash
        if filter_type == 'premium':
            sevimlilar = sevimlilar.filter(mahsulot__is_premium=True)
        elif filter_type == 'regular':
            sevimlilar = sevimlilar.filter(mahsulot__is_premium=False)
        
        # Statistikalar hisoblash
        total_sevimlilar = Sevimli.objects.filter(user=request.user).count()
        premium_sevimlilar = Sevimli.objects.filter(
            user=request.user, 
            mahsulot__is_premium=True
        ).count()
        regular_sevimlilar = total_sevimlilar - premium_sevimlilar
        
        # Sahifalash
        paginator = Paginator(sevimlilar, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'sevimlilar.html', {
            'sevimlilar': page_obj,
            'page_obj': page_obj,
            'filter_type': filter_type,
            'total_count': total_sevimlilar,
            'premium_count': premium_sevimlilar,
            'regular_count': regular_sevimlilar,
        })
    except Exception as e:
        print(f"DEBUG: Xatolik - {e}")
        return render(request, 'sevimlilar.html', {
            'sevimlilar': [],
            'filter_type': 'all',
            'total_count': 0,
            'premium_count': 0,
            'regular_count': 0,
        })

@login_required
def sevimlidan_ochirish_view(request, sevimli_id):
    """Sevimlilardan olib tashlash"""
    try:
        sevimli = get_object_or_404(Sevimli, id=sevimli_id, user=request.user)
        nom = sevimli.mahsulot.name
        sevimli.delete()
        messages.success(request, f'"{nom}" sevimlilardan olib tashlandi.')
        return redirect('sevimlilarim')
    except Exception as e:
        messages.error(request, f'Xatolik yuz berdi: {str(e)}')
        return redirect('sevimlilarim')

# ==================== PROFIL VIEWLARI ====================

@login_required
def my_profile_view(request):
    """O'zimning profilimni ko'rish"""
    try:
        # Profilni topish yoki yaratish
        try:
            profile = SellerProfile.objects.get(user=request.user)
        except SellerProfile.DoesNotExist:
            profile = SellerProfile.objects.create(user=request.user)
        
        # Mening e'lonlarim
        mahsulotlar = Mahsulot.objects.filter(
            user=request.user, 
            aktiv=True
        ).order_by('-id')[:6]
        
        # Premium profil
        premium_profile = None
        try:
            premium_profile = PremiumUser.objects.get(user=request.user)
        except PremiumUser.DoesNotExist:
            pass
        
        # Premium so'rovlar
        premium_requests = PremiumRequest.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
        
        # Statistikalar
        total_products = Mahsulot.objects.filter(user=request.user).count()
        active_products = Mahsulot.objects.filter(user=request.user, aktiv=True, sotilgan=False).count()
        sold_products = Mahsulot.objects.filter(user=request.user, sotilgan=True).count()
        premium_products = Mahsulot.objects.filter(user=request.user, is_premium=True).count()
        
        context = {
            'profile': profile,
            'premium_profile': premium_profile,
            'premium_requests': premium_requests,
            'mahsulotlar': mahsulotlar,
            'total_products': total_products,
            'active_products': active_products,
            'sold_products': sold_products,
            'premium_products': premium_products,
        }
        
        return render(request, 'my_profile.html', context)
        
    except Exception as e:
        print(f"DEBUG my_profile_view: Xatolik - {e}")
        return render(request, 'my_profile.html', {'error': 'Profil yuklanmadi'})

@login_required
def edit_profile_view(request):
    """Profilni tahrirlash"""
    # Profilni topish yoki yaratish
    try:
        profile = SellerProfile.objects.get(user=request.user)
    except SellerProfile.DoesNotExist:
        profile = SellerProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        try:
            # Ma'lumotlarni olish
            profile.bio = request.POST.get('bio', '')
            profile.location = request.POST.get('location', '')
            profile.phone = request.POST.get('phone', '')
            profile.instagram = request.POST.get('instagram', '')
            profile.telegram = request.POST.get('telegram', '')
            
            # Ish vaqtlari
            work_hours_start = request.POST.get('work_hours_start', '09:00')
            work_hours_end = request.POST.get('work_hours_end', '21:00')
            profile.work_hours_start = work_hours_start
            profile.work_hours_end = work_hours_end
            
            # Rasmlarni saqlash
            if 'profile_image' in request.FILES:
                profile.profile_image = request.FILES['profile_image']
            if 'banner_image' in request.FILES:
                profile.banner_image = request.FILES['banner_image']
            
            # Saqlash
            profile.save()
            
            messages.success(request, 'Profil muvaffaqiyatli yangilandi!')
            return redirect('my_profile')
            
        except Exception as e:
            messages.error(request, f'Xatolik yuz berdi: {str(e)}')
    
    context = {
        'profile': profile,
    }
    
    return render(request, 'edit_profile.html', context)

def user_profile_view(request, username):
    """Boshqa foydalanuvchilarning profilini ko'rish"""
    try:
        profile_user = get_object_or_404(User, username=username)
        
        try:
            profile = SellerProfile.objects.get(user=profile_user)
        except SellerProfile.DoesNotExist:
            profile = SellerProfile.objects.create(user=profile_user)
        
        mahsulotlar = Mahsulot.objects.filter(
            user=profile_user, 
            aktiv=True,
            sotilgan=False
        ).order_by('-is_premium', '-premium_priority', '-sana')
        
        paginator = Paginator(mahsulotlar, 9)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Statistikalar
        total_products = Mahsulot.objects.filter(user=profile_user).count()
        active_products = Mahsulot.objects.filter(user=profile_user, aktiv=True, sotilgan=False).count()
        sold_products = Mahsulot.objects.filter(user=profile_user, sotilgan=True).count()
        premium_products = Mahsulot.objects.filter(user=profile_user, is_premium=True).count()
        
        context = {
            'profile_user': profile_user,
            'profile': profile,
            'mahsulotlar': page_obj,
            'page_obj': page_obj,
            'total_products': total_products,
            'active_products': active_products,
            'sold_products': sold_products,
            'premium_products': premium_products,
        }
        
        return render(request, 'user_profile.html', context)
        
    except Exception as e:
        print(f"DEBUG user_profile_view: Xatolik - {e}")
        return render(request, 'user_profile.html', {'error': 'Profil topilmadi'})

# ==================== BOSHQALAR ====================

def qosjso_view(request):
    return render(request, 'qosjso.html')

def bizhaqimizda_view(request):
    return render(request, 'bizhaqimizda.html')

def boglanish_view(request):
    return render(request, 'boglanish.html')

def test_404(request):
    """404 sahifasini ko'rsatish"""
    return HttpResponseNotFound(render(request, '404.html'))

def newnav(request):
    return render(request, 'newnav.html')

def kategoriya1(request):
    return render(request, 'kategoriya1.html')

def qoidalar(request):
    return render(request, 'qoidalar.html')

def maxfiyliksiyosati(request):
    return render(request, 'maxfiyliksiyosati.html')

# ==================== CRON VIEWLARI ====================

@csrf_exempt
@require_POST
def cron_check_premium_expiry(request):
    """CRON endpoint for checking premium expiry"""
    # Faqat ma'lum IP manzillardan kirishga ruxsat
    allowed_ips = ['127.0.0.1', 'localhost', '::1']
    client_ip = request.META.get('REMOTE_ADDR')
    
    # Agar IP manzil ro'yxatda bo'lmasa va superuser bo'lmasa
    if client_ip not in allowed_ips and not request.user.is_superuser:
        return JsonResponse({'error': 'Ruxsat etilmagan'}, status=403)
    
    try:
        result = check_and_update_premium_expiry()
        
        if result:
            return JsonResponse({
                'success': True,
                'message': f'Premium muddati tekshirildi. {result["expired_users"]} foydalanuvchi, {result["expired_products"]} mahsulot, {result["expired_requests"]} so\'rov deaktivlashtirildi. {result["notified_users"]} foydalanuvchi ogohlantirildi.',
                'details': result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Tekshirishda xatolik yuz berdi'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_GET
def check_premium_access_view(request):
    """Premium qo'shish huquqini tekshirish (AJAX)"""
    try:
        premium_profile = PremiumUser.objects.get(user=request.user)
        settings = AdminPremiumSettings.get_settings()
        
        has_access, reason = check_premium_access(request.user)
        
        if has_access:
            # Qo'shish mumkin bo'lgan mahsulotlar sonini tekshirish
            can_add, add_reason = premium_profile.can_add_more_premium_products()
            
            return JsonResponse({
                'success': True,
                'has_access': True,
                'can_add_more': can_add,
                'remaining': premium_profile.get_remaining_premium_products(),
                'total_limit': premium_profile.premium_limit,
                'premium_used': premium_profile.premium_used,
                'message': add_reason if can_add else 'Premium huquq mavjud',
                'days_remaining': premium_profile.get_days_remaining()
            })
        else:
            return JsonResponse({
                'success': False,
                'has_access': False,
                'message': reason,
                'admin_phone': settings.admin_contact_phone,
                'admin_telegram': settings.admin_contact_telegram,
                'admin_email': settings.admin_contact_email,
                'reason': reason
            })
            
    except PremiumUser.DoesNotExist:
        settings = AdminPremiumSettings.get_settings()
        return JsonResponse({
            'success': False,
            'has_access': False,
            'message': 'Premium profil topilmadi',
            'admin_phone': settings.admin_contact_phone,
            'admin_telegram': settings.admin_contact_telegram,
            'admin_email': settings.admin_contact_email,
            'reason': 'Premium profil yo\'q'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'has_access': False,
            'message': f'Xatolik yuz berdi: {str(e)}'
        })





















# ==================== YANGI QO'SHILGAN FUNKSIYALAR ====================

# views.py oxiridagi admin_premium_request_details funksiyasini to'g'rilash

@login_required
@user_passes_test(is_admin)
@require_GET
def admin_premium_request_details(request, request_id):
    """Premium so'rov tafsilotlarini olish (AJAX uchun)"""
    try:
        premium_request = get_object_or_404(PremiumRequest, id=request_id)
        
        # PremiumUser ma'lumotlari
        premium_user = None
        try:
            premium_user = PremiumUser.objects.get(user=premium_request.user)
        except PremiumUser.DoesNotExist:
            pass
        
        # Telegram va Email uchun o'zgaruvchilar
        telegram_display = f"@{premium_request.telegram_username}" if premium_request.telegram_username else "Yo'q"
        email_display = premium_request.email if premium_request.email else "Yo'q"
        premium_end_display = premium_user.premium_end.strftime('%d.%m.%Y') if premium_user and premium_user.premium_end else "Yo'q"
        
        # HTML yaratish
        html = f"""
        <div class="request-details">
            <div class="row">
                <div class="col-md-6">
                    <h6>Asosiy ma'lumotlar</h6>
                    <table class="table table-sm">
                        <tr><td><strong>So'rov ID:</strong></td><td>#{premium_request.id}</td></tr>
                        <tr><td><strong>Foydalanuvchi:</strong></td><td>{premium_request.user.username}</td></tr>
                        <tr><td><strong>To'liq ism:</strong></td><td>{premium_request.full_name}</td></tr>
                        <tr><td><strong>Telefon:</strong></td><td>{premium_request.phone}</td></tr>
                        <tr><td><strong>Telegram:</strong></td><td>{telegram_display}</td></tr>
                        <tr><td><strong>Email:</strong></td><td>{email_display}</td></tr>
                    </table>
                </div>
                
                <div class="col-md-6">
                    <h6>Premium sozlamalar</h6>
                    <table class="table table-sm">
                        <tr><td><strong>So'ralgan kunlar:</strong></td><td>{premium_request.requested_days} kun</td></tr>
                        <tr><td><strong>So'ralgan limit:</strong></td><td>{premium_request.requested_limit} ta</td></tr>
                        <tr><td><strong>Jami summa:</strong></td><td>{premium_request.calculated_total:,} so'm</td></tr>
                        <tr><td><strong>Status:</strong></td><td>{premium_request.get_status_display()}</td></tr>
                        <tr><td><strong>Yaratilgan sana:</strong></td><td>{premium_request.created_at.strftime('%d.%m.%Y %H:%M')}</td></tr>
                    </table>
                </div>
            </div>
        """
        
        # PremiumUser holati
        if premium_user:
            html += f"""
            <div class="alert alert-info mt-3">
                <strong>PremiumUser holati:</strong> {premium_user.get_status_display()}
                <br><strong>Premium muddati:</strong> {premium_end_display}
                <br><strong>Premium limit:</strong> {premium_user.premium_limit} ta
                <br><strong>Foydalanilgan:</strong> {premium_user.premium_used} ta
            </div>
            """
        else:
            # PremiumUser mavjud yo'q
            html += """
            <div class="alert alert-warning mt-3">
                <strong>PremiumUser holati:</strong> Premium profil yo'q
            </div>
            """
        
        # Admin izohlari
        if premium_request.admin_notes:
            admin_notes_display = premium_request.admin_notes.replace('\n', '<br>')
            html += f"""
            <div class="alert alert-warning mt-3">
                <strong>Admin izohlari:</strong><br>{admin_notes_display}
            </div>
            """
        
        # Foydalanuvchi eslatmasi
        if premium_request.notes:
            notes_display = premium_request.notes.replace('\n', '<br>')
            html += f"""
            <div class="alert alert-light mt-3">
                <strong>Foydalanuvchi eslatmasi:</strong><br>{notes_display}
            </div>
            """
        
        # Agar tasdiqlangan bo'lsa
        if premium_request.status == 'approved' and premium_request.admin_user:
            approved_at_display = premium_request.approved_at.strftime('%d.%m.%Y %H:%M') if premium_request.approved_at else "Yo'q"
            html += f"""
            <div class="alert alert-success mt-3">
                <strong>Tasdiqlagan admin:</strong> {premium_request.admin_user.username}
                <br><strong>Tasdiqlangan sana:</strong> {approved_at_display}
            </div>
            """
        
        # Agar rad etilgan bo'lsa
        elif premium_request.status == 'rejected':
            if premium_request.admin_notes:
                admin_notes_display = premium_request.admin_notes.replace('\n', '<br>')
                html += f"""
                <div class="alert alert-danger mt-3">
                    <strong>Rad etilgan</strong>
                    <br><strong>Sabab:</strong> {admin_notes_display}
                </div>
                """
            else:
                html += """
                <div class="alert alert-danger mt-3">
                    <strong>Rad etilgan</strong>
                </div>
                """
        
        html += "</div>"
        
        return JsonResponse({
            'success': True,
            'html': html,
            'request_id': request_id,
            'user': premium_request.user.username,
            'status': premium_request.status
        })
        
    except PremiumRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'So\'rov topilmadi'})
    except Exception as e:
        print(f"admin_premium_request_details xatosi: {e}")
        return JsonResponse({'success': False, 'error': str(e)})












# ==================== ADMIN VIEWLARI ====================

@login_required
@require_GET
def check_premium_access_view(request):
    """Premium qo'shish huquqini tekshirish (AJAX)"""
    try:
        has_access, reason = check_premium_access(request.user)
        
        if has_access:
            # Qo'shish mumkin bo'lgan mahsulotlar sonini tekshirish
            premium_profile = PremiumUser.objects.get(user=request.user)
            can_add, add_reason = premium_profile.can_add_more_premium_products()
            
            return JsonResponse({
                'success': True,
                'has_access': True,
                'can_add_more': can_add,
                'remaining': premium_profile.get_remaining_premium_products(),
                'total_limit': premium_profile.premium_limit,
                'premium_used': premium_profile.premium_used,
                'message': add_reason if can_add else 'Premium huquq mavjud',
                'days_remaining': premium_profile.get_days_remaining()
            })
        else:
            return JsonResponse({
                'success': False,
                'has_access': False,
                'message': reason,
                'admin_phone': AdminPremiumSettings.get_settings().admin_contact_phone,
                'admin_telegram': AdminPremiumSettings.get_settings().admin_contact_telegram,
                'admin_email': AdminPremiumSettings.get_settings().admin_contact_email,
                'reason': reason
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'has_access': False,
            'message': f'Xatolik yuz berdi: {str(e)}'
        })
    """Premium qo'shish huquqini tekshirish (AJAX)"""
    try:
        premium_profile = PremiumUser.objects.get(user=request.user)
        settings = AdminPremiumSettings.get_settings()
        
        has_access, reason = check_premium_access(request.user)
        
        if has_access:
            # Qo'shish mumkin bo'lgan mahsulotlar sonini tekshirish
            can_add, add_reason = premium_profile.can_add_more_premium_products()
            
            return JsonResponse({
                'success': True,
                'has_access': True,
                'can_add_more': can_add,
                'remaining': premium_profile.get_remaining_premium_products(),
                'total_limit': premium_profile.premium_limit,
                'premium_used': premium_profile.premium_used,
                'message': add_reason if can_add else 'Premium huquq mavjud',
                'days_remaining': premium_profile.get_days_remaining()
            })
        else:
            return JsonResponse({
                'success': False,
                'has_access': False,
                'message': reason,
                'admin_phone': settings.admin_contact_phone,
                'admin_telegram': settings.admin_contact_telegram,
                'admin_email': settings.admin_contact_email,
                'reason': reason
            })
            
    except PremiumUser.DoesNotExist:
        settings = AdminPremiumSettings.get_settings()
        return JsonResponse({
            'success': False,
            'has_access': False,
            'message': 'Premium profil topilmadi',
            'admin_phone': settings.admin_contact_phone,
            'admin_telegram': settings.admin_contact_telegram,
            'admin_email': settings.admin_contact_email,
            'reason': 'Premium profil yo\'q'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'has_access': False,
            'message': f'Xatolik yuz berdi: {str(e)}'
        })







# views.py - yangi funksiya qo'shing

@login_required
def check_premium_before_request(request):
    """Premium so'rov yuborishdan oldin tekshirish"""
    try:
        try:
            premium_profile = PremiumUser.objects.get(user=request.user)
            
            context = {
                'has_premium': premium_profile.is_premium,
                'premium_profile': premium_profile,
                'title': 'Premium Holatni Tekshirish',
            }
            
            if premium_profile.is_premium and premium_profile.status == 'active':
                if premium_profile.premium_end and premium_profile.premium_end > timezone.now():
                    qolgan_kunlar = (premium_profile.premium_end - timezone.now()).days
                    premium_tugash_sana = premium_profile.premium_end.strftime('%d.%m.%Y')
                    
                    context.update({
                        'has_active_premium': True,
                        'days_remaining': qolgan_kunlar,
                        'premium_end_date': premium_tugash_sana,
                        'message': (
                            f"Sizda aktiv Premium obuna mavjud! "
                            f"Premium {qolgan_kunlar} kundan keyin ({premium_tugash_sana}) tugaydi. "
                            f"Premium tugagach yangi so'rov yuborishingiz mumkin."
                        )
                    })
            
            return render(request, 'check_premium_before_request.html', context)
            
        except PremiumUser.DoesNotExist:
            # Premium profili yo'q, so'rov yuborish mumkin
            return redirect('submit_premium_request')
            
    except Exception as e:
        print(f"check_premium_before_request error: {e}")
        messages.error(request, "Tekshirishda xatolik yuz berdi")
        return redirect('my_profile')




# views.py - check_premium_status_view funksiyasini topamiz


@login_required
def check_premium_status_view(request):
    """Foydalanuvchining premium holatini tekshirish"""
    try:
        premium_profile = None
        is_premium = False
        premium_info = {}
        
        try:
            premium_profile = PremiumUser.objects.get(user=request.user)
            is_premium = premium_profile.is_premium
            
            # Premium mahsulotlar sonini hisoblash
            premium_products_count = Mahsulot.objects.filter(
                user=request.user,
                is_premium=True,
                premium_expiry__gt=timezone.now()
            ).count()
            
            # Counter to'g'rilash
            if premium_profile.premium_used != premium_products_count:
                premium_profile.premium_used = premium_products_count
                premium_profile.save(update_fields=['premium_used'])
            
            # Premium tugash vaqtini tekshirish
            premium_end_date = None
            days_remaining = 0
            premium_status = "Yo'q"
            
            if premium_profile.is_premium and premium_profile.premium_end:
                now = timezone.now()
                if premium_profile.premium_end > now:
                    days_remaining = (premium_profile.premium_end - now).days
                    premium_end_date = premium_profile.premium_end.strftime('%d.%m.%Y %H:%M')
                    if days_remaining > 0:
                        premium_status = f"Aktiv ({days_remaining} kun qoldi)"
                    else:
                        premium_status = "Bugun tugaydi"
                else:
                    # Premium muddati tugagan
                    premium_status = "Muddati tugagan"
                    
                    # Avtomatik deaktivlashtirish
                    if premium_profile.is_premium:
                        premium_profile.deactivate_premium()
                        is_premium = False
            else:
                premium_status = premium_profile.get_status_display()
            
            premium_info = {
                'id': premium_profile.id,
                'is_premium': is_premium,
                'status': premium_profile.status,
                'status_display': premium_status,
                'admin_approved': getattr(premium_profile, 'admin_approved', False),
                'premium_start': premium_profile.premium_start.strftime('%d.%m.%Y %H:%M') if getattr(premium_profile, 'premium_start', None) else None,
                'premium_end': premium_end_date,
                'premium_days': getattr(premium_profile, 'premium_days', 0),
                'premium_limit': getattr(premium_profile, 'premium_limit', 0),
                'premium_used': getattr(premium_profile, 'premium_used', 0),
                'remaining_products': max(0, getattr(premium_profile, 'premium_limit', 0) - getattr(premium_profile, 'premium_used', 0)),
                'days_remaining': days_remaining,
            }
            
        except PremiumUser.DoesNotExist:
            premium_info = {
                'is_premium': False,
                'status': 'no_premium',
                'status_display': 'Premium yo\'q',
                'message': 'Sizda premium profil mavjud emas. Premium so\'rov yuboring.',
                'can_add_premium': False,
                'can_add_message': 'Premium profilingiz yo\'q',
            }
        
        # Premium mahsulotlarni olish (LIST sifatida)
        premium_products_list = list(Mahsulot.objects.filter(
            user=request.user,
            is_premium=True
        ).order_by('-premium_since')[:10])
        
        # Premium so'rovlarni olish (LIST sifatida)
        premium_requests_list = list(PremiumRequest.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5])
        
        # So'rovlar statistikasi
        stats = {
            'total_requests': PremiumRequest.objects.filter(user=request.user).count(),
            'pending_requests': PremiumRequest.objects.filter(user=request.user, status='pending').count(),
            'approved_requests': PremiumRequest.objects.filter(user=request.user, status='approved').count(),
            'rejected_requests': PremiumRequest.objects.filter(user=request.user, status='rejected').count(),
        }
        
        context = {
            'premium_info': premium_info,
            'premium_products': premium_products_list,  # LIST
            'premium_requests': premium_requests_list,  # LIST
            'stats': stats,
            'title': 'Premium Holatim',
            'description': 'Premium obuna holatingiz va huquqlaringiz',
            'is_premium_user': is_premium,
        }
        
        return render(request, 'check_premium_status.html', context)
        
    except Exception as e:
        print(f"Check premium status error: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Premium holatingizni tekshirishda xatolik: {str(e)}")
        return render(request, 'check_premium_status.html', {
            'error': str(e),
            'premium_info': {'is_premium': False},
            'title': 'Premium Holatim',
        })






@login_required
def submit_premium_request_view(request):
    """Premium huquq so'rovini yuborish"""
    try:
        print(f"DEBUG: submit_premium_request_view called. Method: {request.method}")
        print(f"DEBUG: User: {request.user.username}")
        
        # PRE-TEKSHRUV: Foydalanuvchining aktiv Premium obunasini tekshirish
        try:
            premium_profile = PremiumUser.objects.get(user=request.user)
            
            if premium_profile.is_premium and premium_profile.status == 'active':
                if premium_profile.premium_end and premium_profile.premium_end > timezone.now():
                    qolgan_kunlar = (premium_profile.premium_end - timezone.now()).days
                    premium_tugash_sana = premium_profile.premium_end.strftime('%d.%m.%Y')
                    
                    messages.error(request, 
                        f"❌ Sizda aktiv Premium obuna mavjud! "
                        f"Premium {qolgan_kunlar} kundan keyin ({premium_tugash_sana}) tugaydi. "
                        f"Premium tugagach yangi so'rov yuborishingiz mumkin."
                    )
                    
                    return redirect('check_premium_status')
                    
        except PremiumUser.DoesNotExist:
            print(f"DEBUG: PremiumUser does not exist for {request.user.username}")
            pass
        
        # Premium sozlamalarni olish
        try:
            settings = AdminPremiumSettings.get_settings()
            print(f"DEBUG: Got settings")
        except Exception as e:
            print(f"DEBUG: Error getting settings: {e}")
            settings = None
        
        if settings and not getattr(settings, 'is_premium_enabled', True):
            messages.error(request, "Premium tizim hozirda faol emas.")
            return redirect('my_profile')
        
        # Foydalanuvchining oylik so'rov limitini tekshirish
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_requests = PremiumRequest.objects.filter(
            user=request.user,
            created_at__gte=current_month,
            status__in=['pending', 'approved']
        ).count()
        
        max_requests = getattr(settings, 'max_premium_requests_per_user', 3) if settings else 3
        requests_left = max(0, max_requests - this_month_requests)
        
        print(f"DEBUG: requests_left: {requests_left}, max_requests: {max_requests}")
        
        if requests_left <= 0:
            messages.error(request, 
                f"Siz oy uchun maksimum {max_requests} ta so'rov yubora olasiz. "
                f"Keyingi oyda qayta urinib ko'ring."
            )
            return redirect('my_premium_requests')
        
        # GET so'rovi uchun kontekst tayyorlash
        context = {
            'settings': settings,
            'payment_methods': ['Bank karta', 'Click', 'Payme', 'Uzumbank'],
            'bank_info': {
                'card_number': '8600 1234 5678 9012',
                'bank_name': 'HUMO',
                'card_owner': 'TEZ SOT',
            },
            'discount_active': False,
            'discount_percentage': 0,
            'requests_left': requests_left,
            'max_requests': max_requests,
            'user': request.user,
            'user_profile': getattr(request.user, 'seller_profile', None),
            'title': 'Premium So\'rov Yuborish',
            'description': 'Premium obuna uchun so\'rov yuboring',
            'form_data': {}
        }
        
        # POST so'rovi
        if request.method == 'POST':
            print("=" * 50)
            print("DEBUG: POST REQUEST RECEIVED")
            print("=" * 50)
            print(f"DEBUG: POST data keys: {list(request.POST.keys())}")
            
            # CSRF tokenni tekshirish
            csrf_token = request.POST.get('csrfmiddlewaretoken')
            print(f"DEBUG: CSRF token present: {bool(csrf_token)}")
            
            try:
                # Form ma'lumotlarini olish
                full_name = request.POST.get('full_name', '').strip()
                phone = request.POST.get('phone', '').strip()
                telegram_username = request.POST.get('telegram_username', '').strip()
                email = request.POST.get('email', '').strip()
                requested_days = request.POST.get('requested_days', '30')
                requested_limit = request.POST.get('requested_limit', '5')
                notes = request.POST.get('notes', '').strip()
                auto_approve = request.POST.get('auto_approve') == 'on'
                payment_method = request.POST.get('payment_method', '')
                
                # DEBUG: Qiymatlarni ko'rish
                print(f"DEBUG: full_name: {full_name}")
                print(f"DEBUG: phone: {phone}")
                print(f"DEBUG: payment_method: {payment_method}")
                print(f"DEBUG: requested_days: {requested_days}")
                print(f"DEBUG: requested_limit: {requested_limit}")
                print(f"DEBUG: auto_approve: {auto_approve}")
                
                # Validatsiya
                validation_errors = []
                
                if not full_name:
                    validation_errors.append("Iltimos, ism familiya kiriting")
                
                if not phone:
                    validation_errors.append("Iltimos, telefon raqam kiriting")
                else:
                    cleaned_phone = re.sub(r'\D', '', phone)
                    if len(cleaned_phone) < 9:
                        validation_errors.append("Telefon raqami noto'g'ri formatda")
                
                if not requested_days or int(requested_days) < 1:
                    validation_errors.append("Premium kunlari 1 dan 365 gacha bo'lishi kerak")
                
                if not requested_limit or int(requested_limit) < 1:
                    validation_errors.append("Mahsulot limiti 1 dan 50 gacha bo'lishi kerak")
                
                if not payment_method:
                    validation_errors.append("Iltimos, to'lov usulini tanlang")
                
                if validation_errors:
                    print(f"DEBUG: Validation errors: {validation_errors}")
                    for error in validation_errors:
                        messages.error(request, error)
                    
                    context['form_data'] = {
                        'full_name': full_name,
                        'phone': phone,
                        'telegram_username': telegram_username,
                        'email': email,
                        'requested_days': requested_days,
                        'requested_limit': requested_limit,
                        'notes': notes,
                        'auto_approve': auto_approve,
                        'payment_method': payment_method,
                    }
                    
                    return render(request, 'submit_premium_request.html', context)
                
                # Telegram username ni tozalash
                if telegram_username and telegram_username.startswith('@'):
                    telegram_username = telegram_username[1:]
                
                # Narxni hisoblash (soddalashtirilgan)
                price_per_day = 2000
                price_per_product = 15000
                calculated_total = (int(requested_days) * price_per_day) + (int(requested_limit) * price_per_product)
                
                print(f"DEBUG: calculated_total: {calculated_total}")
                
                # Premium so'rov yaratish
                print(f"DEBUG: Creating PremiumRequest object...")
                
                premium_request = PremiumRequest.objects.create(
                    user=request.user,
                    full_name=full_name,
                    phone=cleaned_phone,
                    telegram_username=telegram_username,
                    email=email,
                    requested_days=int(requested_days),
                    requested_limit=int(requested_limit),
                    notes=notes,
                    calculated_total=calculated_total,
                    payment_amount=calculated_total,
                    payment_method=payment_method,
                    auto_approve=auto_approve,
                    status='pending',
                    payment_status='pending'
                )
                
                print(f"DEBUG: PremiumRequest created with ID: {premium_request.id}")
                
                # To'lov dalili
                if 'payment_proof' in request.FILES:
                    print(f"DEBUG: Payment proof file found")
                    premium_request.payment_proof = request.FILES['payment_proof']
                    premium_request.save()
                
                # Muvaffaqiyatli xabar
                success_message = f"""
                ✅ Premium so'rovingiz muvaffaqiyatli yuborildi!
                
                📋 So'rov raqami: #{premium_request.id}
                👤 Ism: {full_name}
                📞 Telefon: {cleaned_phone}
                📅 Premium muddati: {requested_days} kun
                📦 Mahsulot limiti: {requested_limit} ta
                💰 Jami to'lov: {calculated_total:,.0f} so'm
                💳 To'lov usuli: {payment_method}
                {'🚀 Toʻlov tasdiqlangandan soʻng avtomatik tasdiqlanadi' if auto_approve else '⏳ Admin tasdigini kuting'}
                """
                
                messages.success(request, success_message)
                
                print(f"DEBUG: Success message added. Redirecting to my_premium_requests...")
                return redirect('my_premium_requests')
                
            except ValueError as e:
                print(f"DEBUG: ValueError in POST: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"Raqamli qiymatda xatolik: {str(e)}")
                context['form_data'] = request.POST.dict()
                return render(request, 'submit_premium_request.html', context)
            except Exception as e:
                print(f"DEBUG: General error in POST: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"So'rovni yuborishda xatolik: {str(e)}")
                context['form_data'] = request.POST.dict()
                return render(request, 'submit_premium_request.html', context)
        
        print(f"DEBUG: Rendering GET request")
        return render(request, 'submit_premium_request.html', context)
        
    except Exception as e:
        print(f"DEBUG: Outer error: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Sahifani yuklashda xatolik yuz berdi: {str(e)}")
        return redirect('my_profile')



from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import (
    PremiumRequest, PremiumUser, AdminPremiumSettings, 
    PremiumNotification, SellerProfile
)
import json

@login_required
def create_premium_request(request):
    # Foydalanuvchining premium holatini tekshirish
    try:
        premium_user = PremiumUser.objects.get(user=request.user)
        
        # Agar foydalanuvchi allaqachon premium bo'lsa va muddati tugamagan bo'lsa
        if premium_user.is_premium and premium_user.status == 'active':
            if premium_user.premium_end and premium_user.premium_end > timezone.now():
                days_left = (premium_user.premium_end - timezone.now()).days
                premium_end_date = premium_user.premium_end.strftime('%d.%m.%Y')
                
                messages.warning(
                    request,
                    f"Sizda aktiv Premium obuna mavjud! Premium {days_left} kundan keyin "
                    f"({premium_end_date}) tugaydi. Premium tugagach yangi so'rov yuborishingiz mumkin."
                )
                return redirect('dashboard')
    except PremiumUser.DoesNotExist:
        pass
    
    # Admin sozlamalarini olish
    settings = AdminPremiumSettings.get_settings()
    
    # Foydalanuvchining oyiga qancha so'rov yuborganligini hisoblash
    one_month_ago = timezone.now() - timedelta(days=30)
    user_requests_count = PremiumRequest.objects.filter(
        user=request.user,
        created_at__gte=one_month_ago
    ).count()
    
    # Limitni tekshirish
    max_requests = settings.max_premium_requests_per_user
    requests_left = max_requests - user_requests_count
    
    # Agar limit tugagan bo'lsa
    if requests_left <= 0:
        context = {
            'title': 'Premium So\'rov',
            'requests_left': 0,
            'max_requests': max_requests,
            'settings': settings,
        }
        return render(request, 'premium_request_form.html', context)
    
    # Forma ma'lumotlari
    form_data = {}
    
    if request.method == 'POST':
        # Forma ma'lumotlarini olish
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        telegram_username = request.POST.get('telegram_username', '').strip()
        email = request.POST.get('email', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        requested_days = int(request.POST.get('requested_days', 30))
        requested_limit = int(request.POST.get('requested_limit', 5))
        calculated_total = float(request.POST.get('calculated_total', 0))
        
        payment_method = request.POST.get('payment_method', '')
        auto_approve = request.POST.get('auto_approve') == 'on'
        
        # Forma ma'lumotlarini saqlash (agar xato bo'lsa, qayta ko'rsatish uchun)
        form_data = {
            'full_name': full_name,
            'phone': phone,
            'telegram_username': telegram_username,
            'email': email,
            'notes': notes,
            'requested_days': requested_days,
            'requested_limit': requested_limit,
            'calculated_total': calculated_total,
            'payment_method': payment_method,
            'auto_approve': auto_approve,
        }
        
        # Validation
        errors = []
        
        if not full_name:
            errors.append("To'liq ism kiritilishi shart")
        
        if not phone:
            errors.append("Telefon raqami kiritilishi shart")
        elif len(phone) != 9 and len(phone) != 12:
            errors.append("Telefon raqami noto'g'ri formatda")
        
        if requested_days < 1 or requested_days > 365:
            errors.append("Premium kunlari 1 dan 365 gacha bo'lishi kerak")
        
        if requested_limit < 1 or requested_limit > 50:
            errors.append("Mahsulot limiti 1 dan 50 gacha bo'lishi kerak")
        
        if not payment_method:
            errors.append("To'lov usulini tanlash shart")
        
        # Agar xatolar bo'lsa
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                # PremiumRequest yaratish
                premium_request = PremiumRequest.objects.create(
                    user=request.user,
                    full_name=full_name,
                    phone=phone,
                    telegram_username=telegram_username if telegram_username else None,
                    email=email if email else None,
                    notes=notes if notes else None,
                    requested_days=requested_days,
                    requested_limit=requested_limit,
                    calculated_total=calculated_total,
                    payment_amount=calculated_total,
                    payment_method=payment_method,
                    auto_approve=auto_approve,
                    status='pending',
                    payment_status='pending',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
                
                # Foydalanuvchiga bildirishnoma
                PremiumNotification.objects.create(
                    user=request.user,
                    notification_type='new_request',
                    title="Premium So'rovingiz Qabul Qilindi",
                    message=f"#{premium_request.id} raqamli premium so'rovingiz qabul qilindi va tekshirish uchun yuborildi.",
                    data={
                        'request_id': premium_request.id,
                        'days': requested_days,
                        'limit': requested_limit,
                        'amount': calculated_total,
                    }
                )
                
                # Adminlarga bildirishnoma (agar biron bir admin bor bo'lsa)
                from django.contrib.auth.models import User
                admin_users = User.objects.filter(is_staff=True, is_active=True)
                for admin in admin_users:
                    try:
                        PremiumNotification.objects.create(
                            user=admin,
                            notification_type='admin_action',
                            title="Yangi Premium So'rovi",
                            message=f"{request.user.username} foydalanuvchidan yangi premium so'rovi keldi. ID: #{premium_request.id}",
                            data={
                                'request_id': premium_request.id,
                                'user_id': request.user.id,
                                'username': request.user.username,
                            }
                        )
                    except:
                        pass
                
                messages.success(
                    request,
                    f"Premium so'rovingiz muvaffaqiyatli yuborildi! So'rov raqami: #{premium_request.id}. "
                    f"Adminlarimiz tez orada siz bilan bog'lanishadi."
                )
                
                # So'rov tugagach, foydalanuvchini o'z so'rovlari sahifasiga yo'naltirish
                return redirect('my_premium_requests')
                
            except Exception as e:
                messages.error(
                    request, 
                    f"So'rovni yuborishda xatolik yuz berdi: {str(e)}"
                )
    
    # User ma'lumotlarini olish
    user = request.user
    seller_profile = SellerProfile.objects.filter(user=user).first()
    
    # Agar form_data bo'sh bo'lsa, user ma'lumotlaridan to'ldirish
    if not form_data.get('full_name'):
        form_data['full_name'] = user.get_full_name() or user.username
    
    if not form_data.get('phone') and seller_profile:
        form_data['phone'] = seller_profile.phone
    
    if not form_data.get('telegram_username') and seller_profile:
        form_data['telegram_username'] = seller_profile.telegram
    
    if not form_data.get('email'):
        form_data['email'] = user.email
    
    # Bank ma'lumotlari
    bank_info = {
        'card_number': settings.bank_card_number or '8600 1234 5678 9012',
        'card_owner': settings.bank_card_owner or 'John Doe',
        'bank_name': settings.bank_name or 'Turon Bank',
    }
    
    # To'lov usullari
    payment_methods = settings.get_payment_methods_list()
    
    context = {
        'title': 'Premium So\'rov',
        'requests_left': requests_left,
        'max_requests': max_requests,
        'form_data': form_data,
        'settings': settings,
        'bank_info': bank_info,
        'payment_methods': payment_methods,
        'user': user,
    }
    
    return render(request, 'premium_request_form.html', context)


# views.py ga qo'shimcha

from .search_service import SearchService
from .models import SearchLog, Mahsulot
from django.core.paginator import Paginator
from django.views.decorators.cache import cache_page
from django.core.cache import cache

@require_GET
def advanced_search(request):
    """Kengaytirilgan qidiruv"""
    query = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)
    
    # Qidiruv logini saqlash
    if query:
        SearchLog.objects.create(
            query=query,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR'),
            results_count=0
        )
    
    # Kechiktirilgan yuklash uchun cache
    cache_key = f"search_{query}_{page}"
    cached_result = cache.get(cache_key)
    
    if cached_result and request.GET.get('no_cache') != '1':
        return JsonResponse(cached_result)
    
    if len(query) < 2:
        context = {
            'results': [],
            'suggestions': [],
            'has_results': False,
            'popular_searches': get_popular_searches(),
        }
        cache.set(cache_key, context, 60)  # 1 daqiqa cache
        return JsonResponse(context)
    
    # Qidiruvni amalga oshirish
    search_result = SearchService.search_with_suggestions(query)
    
    # Sahifalash
    paginator = Paginator(search_result['results'], 20)
    page_obj = paginator.get_page(page)
    
    # Natijalar sonini logga yozish
    if query:
        SearchLog.objects.filter(
            query=query,
            ip_address=request.META.get('REMOTE_ADDR')
        ).order_by('-created_at').first().update(
            results_count=paginator.count
        )
    
    # Formatlash
    products_data = []
    for product in page_obj:
        products_data.append({
            'id': product.id,
            'name': product.name,
            'price': product.narx_formatted(),
            'category': product.get_category_display(),
            'image': product.asosiyimg.url if product.asosiyimg else None,
            'url': f"/mahsulot/{product.id}/",
            'is_premium': product.is_premium,
            'similarity': round(getattr(product, 'final_score_boosted', 50), 1),
            'seller': product.user.username,
        })
    
    response_data = {
        'results': products_data,
        'suggestions': search_result['suggestions'],
        'has_results': search_result['has_results'],
        'total_count': paginator.count,
        'page': page_obj.number,
        'total_pages': paginator.num_pages,
        'query': query,
        'normalized_query': search_result['normalized_query'],
        'popular_searches': get_popular_searches(),
    }
    
    # Cachelash (5 daqiqa)
    cache.set(cache_key, response_data, 300)
    
    return JsonResponse(response_data)

def get_popular_searches(days=7, limit=10):
    """Mashhur qidiruvlarni olish"""
    from django.utils import timezone
    from datetime import timedelta
    
    cache_key = f'popular_searches_{days}'
    cached = cache.get(cache_key)
    
    if cached:
        return cached
    
    start_date = timezone.now() - timedelta(days=days)
    
    popular = SearchLog.objects.filter(
        created_at__gte=start_date
    ).values('query').annotate(
        count=models.Count('id')
    ).order_by('-count')[:limit]
    
    result = list(popular)
    cache.set(cache_key, result, 3600)  # 1 soat cache
    
    return result

@require_GET
def search_autocomplete(request):
    """Autocomplete takliflari (real-time)"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    cache_key = f'autocomplete_{query}'
    cached = cache.get(cache_key)
    
    if cached:
        return JsonResponse(cached, safe=False)
    
    normalized_query = SearchService.normalize_word(query)
    
    # Mahsulot nomlaridan takliflar
    products = Mahsulot.objects.filter(
        aktiv=True,
        sotilgan=False
    ).values_list('name', flat=True).distinct()[:50]
    
    suggestions = []
    for product in products:
        similarity = SearchService.calculate_similarity(query, product)
        if similarity >= 40:
            suggestions.append({
                'text': product,
                'similarity': similarity,
                'type': 'product'
            })
    
    # Kategoriyalardan takliflar
    categories = dict(Mahsulot.CATEGORY_CHOICES)
    for cat_key, cat_name in categories.items():
        similarity = SearchService.calculate_similarity(query, cat_name)
        if similarity >= 40:
            suggestions.append({
                'text': cat_name,
                'similarity': similarity,
                'type': 'category',
                'url': f'/kategoriya/{cat_key}/'
            })
    
    # Common typo takliflari
    for typo, correction in SearchService.COMMON_TYPOS.items():
        if query in typo or typo in query:
            suggestions.append({
                'text': correction,
                'similarity': 80,
                'type': 'suggestion',
                'is_correction': True
            })
    
    # O'xshashlik bo'yicha saralash
    suggestions.sort(key=lambda x: x['similarity'], reverse=True)
    
    cache.set(cache_key, suggestions[:15], 300)  # 5 daqiqa cache
    
    return JsonResponse(suggestions[:15], safe=False)

# ==================== QIDIRUV FUNKSIYALARI (YAQIN SO'ZLARNI TOPISH) ====================
def normalize_text(text):
    """Matnni normalize qilish - so'z ildizlarini aniqlash"""
    if not text:
        return ""
    
    text = str(text).lower()
    
    # O'zbekcha so'z ildizlarini aniqlash (stemming)
    word_endings = ['lar', 'ning', 'ga', 'ni', 'da', 'dan', 'miz', 'siz', 'iz', 'ning']
    
    for ending in word_endings:
        if text.endswith(ending):
            text = text[:-len(ending)]
            break
    
    # Harf almashtirishlar
    replacements = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'е': 'e', 'ё': 'yo', 'ж': 'j', 'з': 'z', 'и': 'i',
        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
        'у': 'u', 'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'i', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya',
        'ў': 'u', 'ғ': 'g', 'қ': 'q', 'ҳ': 'h',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


def api_search(request):
    """Real-time qidiruv API - so'z ildizlarini aniqlash bilan"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    try:
        # Normalize qilingan query
        normalized_query = normalize_text(query)
        
        # So'z ildizini olish (masalan: kitoblar -> kitob)
        root_query = normalized_query
        if normalized_query.endswith('lar'):
            root_query = normalized_query[:-3]
        elif normalized_query.endswith('ning'):
            root_query = normalized_query[:-4]
        elif normalized_query.endswith('ga') or normalized_query.endswith('ni'):
            root_query = normalized_query[:-2]
        
        # Mahsulotlarni qidirish - bir nechta variantlar bilan
        mahsulotlar = Mahsulot.objects.filter(
            aktiv=True,
            sotilgan=False
        ).filter(
            # To'g'ridan-to'g'ri moslik
            Q(name__icontains=query) |
            # Normalize qilingan moslik
            Q(name__icontains=normalized_query) |
            # So'z ildizi mosligi (kitoblar -> kitob)
            Q(name__icontains=root_query) |
            # Kategoriya bo'yicha
            Q(category__icontains=normalized_query) |
            Q(category__icontains=root_query) |
            # Tavsifda qidirish
            Q(tavsif__icontains=normalized_query) |
            Q(tavsif__icontains=root_query) |
            # Mahsulot turi
            Q(mahsulotturi__icontains=normalized_query)
        ).order_by('-is_premium', '-premium_priority', '-sana')[:20]
        
        results = []
        for product in mahsulotlar:
            results.append({
                'id': product.id,
                'name': product.name,
                'price': product.narx_formatted(),
                'category': product.get_category_display(),
                'image': product.asosiyimg.url if product.asosiyimg else None,
                'url': f"/mahsulot/{product.id}/",
                'is_premium': product.is_premium,
                'similarity': 100 if query.lower() in product.name.lower() else 85,
            })
        
        return JsonResponse(results, safe=False)
        
    except Exception as e:
        print(f"DEBUG api_search xatolik: {e}")
        return JsonResponse([], safe=False)


        
def levenshtein_similarity(word1, word2):
    """Levenshtein masofasi asosida o'xshashlik foizini hisoblash"""
    if not word1 or not word2:
        return 0
    
    word1 = normalize_text(word1)
    word2 = normalize_text(word2)
    
    if word1 == word2:
        return 100
    
    # Levenshtein masofasini hisoblash
    len1, len2 = len(word1), len(word2)
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
    
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if word1[i-1] == word2[j-1] else 1
            dp[i][j] = min(
                dp[i-1][j] + 1,      # o'chirish
                dp[i][j-1] + 1,      # qo'shish
                dp[i-1][j-1] + cost  # almashtirish
            )
    
    distance = dp[len1][len2]
    max_len = max(len1, len2)
    similarity = (1 - distance / max_len) * 100
    
    return max(0, similarity)


def jaro_winkler_similarity(word1, word2):
    """Jaro-Winkler o'xshashlik algoritmi - yaqin so'zlarni topish uchun"""
    word1 = normalize_text(word1)
    word2 = normalize_text(word2)
    
    if not word1 or not word2:
        return 0
    
    if word1 == word2:
        return 100
    
    # Jaro similarity
    len1, len2 = len(word1), len(word2)
    match_distance = max(len1, len2) // 2 - 1
    match_distance = max(match_distance, 0)
    
    matches1 = [False] * len1
    matches2 = [False] * len2
    
    matches = 0
    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(len2, i + match_distance + 1)
        for j in range(start, end):
            if not matches2[j] and word1[i] == word2[j]:
                matches1[i] = True
                matches2[j] = True
                matches += 1
                break
    
    if matches == 0:
        return 0
    
    # Transpositions
    k = 0
    transpositions = 0
    for i in range(len1):
        if matches1[i]:
            while not matches2[k]:
                k += 1
            if word1[i] != word2[k]:
                transpositions += 1
            k += 1
    
    transpositions //= 2
    
    jaro = (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3
    
    # Winkler qismi (prefix o'xshashligi)
    prefix_len = 0
    for i in range(min(4, len1, len2)):
        if word1[i] == word2[i]:
            prefix_len += 1
        else:
            break
    
    jaro_winkler = jaro + (prefix_len * 0.1 * (1 - jaro))
    
    return jaro_winkler * 100


def calculate_word_similarity(query, product_name):
    """So'zlar orasidagi o'xshashlikni hisoblash"""
    query = normalize_text(query)
    product_name = normalize_text(product_name)
    
    if not query or not product_name:
        return 0
    
    # 1. To'g'ridan-to'g'ri moslik
    if query == product_name:
        return 100
    
    # 2. Qisman moslik (bir so'z ikkinchisining ichida)
    if query in product_name or product_name in query:
        return 85
    
    # 3. So'zlarni bo'lib tekshirish
    query_words = query.split()
    product_words = product_name.split()
    
    best_similarity = 0
    
    for qw in query_words:
        for pw in product_words:
            if len(qw) >= 2 and len(pw) >= 2:
                # Jaro-Winkler o'xshashligi
                similarity = jaro_winkler_similarity(qw, pw)
                best_similarity = max(best_similarity, similarity)
                
                # Levenshtein o'xshashligi
                lev_sim = levenshtein_similarity(qw, pw)
                best_similarity = max(best_similarity, lev_sim)
    
    # 4. Prefix o'xshashligi (mishka -> mushuk)
    if len(query) >= 3 and len(product_name) >= 3:
        if query[:2] == product_name[:2]:
            best_similarity = max(best_similarity, 65)
        elif query[0] == product_name[0]:
            best_similarity = max(best_similarity, 40)
    
    # 5. Suffiks o'xshashligi
    if len(query) >= 3 and len(product_name) >= 3:
        if query[-2:] == product_name[-2:]:
            best_similarity = max(best_similarity, 55)
    
    # 6. Umumiy harflar ulushi
    common_chars = sum(1 for c in query if c in product_name)
    if len(query) > 0:
        char_similarity = (common_chars / len(query)) * 100
        best_similarity = max(best_similarity, char_similarity * 0.7)
    
    return min(100, best_similarity)


def api_search(request):
    """Real-time qidiruv API - yaqin so'zlarni topish (PostgreSQL talab qilmaydi)"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    try:
        # Normalize qilingan query
        normalized_query = normalize_text(query)
        
        # 1. Avval aniq mosliklarni qidirish
        exact_matches = Mahsulot.objects.filter(
            aktiv=True,
            sotilgan=False
        ).filter(
            Q(name__icontains=query) |
            Q(name__icontains=normalized_query) |
            Q(tavsif__icontains=query) |
            Q(category__icontains=query) |
            Q(mahsulotturi__icontains=query)
        ).order_by('-is_premium', '-premium_priority', '-sana')[:30]
        
        exact_ids = [p.id for p in exact_matches]
        
        # 2. Yaqin so'zlar bilan qidirish (exact bo'lmaganlar)
        other_products = Mahsulot.objects.filter(
            aktiv=True,
            sotilgan=False
        ).exclude(id__in=exact_ids).order_by('-is_premium', '-premium_priority', '-sana')[:100]
        
        results = []
        processed_ids = set()
        
        # Exact matchlarni qo'shish
        for product in exact_matches:
            processed_ids.add(product.id)
            results.append({
                'id': product.id,
                'name': product.name,
                'price': product.narx_formatted(),
                'category': product.get_category_display(),
                'image': product.asosiyimg.url if product.asosiyimg else None,
                'url': f"/mahsulot/{product.id}/",
                'is_premium': product.is_premium,
                'similarity': 100,
                'match_type': 'exact'
            })
        
        # Yaqin so'zlarni qidirish
        for product in other_products:
            if product.id in processed_ids:
                continue
            
            similarity = calculate_word_similarity(query, product.name)
            
            # Agar tavsifda ham qidirilsa, qo'shimcha ball
            if similarity < 70 and product.tavsif:
                desc_similarity = calculate_word_similarity(query, product.tavsif[:200])
                similarity = max(similarity, desc_similarity * 0.6)
            
            # Agar kategoriyada bo'lsa
            if similarity < 60 and product.category:
                cat_similarity = calculate_word_similarity(query, product.category)
                similarity = max(similarity, cat_similarity * 0.5)
            
            # 25% dan yuqori o'xshashlik bo'lsa qo'shamiz
            if similarity >= 25:
                match_type = 'fuzzy'
                if similarity >= 80:
                    match_type = 'high'
                elif similarity >= 60:
                    match_type = 'medium'
                else:
                    match_type = 'low'
                
                results.append({
                    'id': product.id,
                    'name': product.name,
                    'price': product.narx_formatted(),
                    'category': product.get_category_display(),
                    'image': product.asosiyimg.url if product.asosiyimg else None,
                    'url': f"/mahsulot/{product.id}/",
                    'is_premium': product.is_premium,
                    'similarity': int(similarity),
                    'match_type': match_type
                })
        
        # O'xshashlik bo'yicha saralash (yuqoridan pastga)
        results.sort(key=lambda x: (-x['similarity'], -x['is_premium']))
        
        # 20 tagacha natija qaytaramiz
        return JsonResponse(results[:20], safe=False)
        
    except Exception as e:
        print(f"DEBUG api_search xatolik: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse([], safe=False)


def api_search_suggestions(request):
    """Qidiruv takliflari - "Did you mean?" funksiyasi"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    try:
        normalized_query = normalize_text(query)
        
        # Barcha mahsulot nomlarini olish
        all_names = Mahsulot.objects.filter(
            aktiv=True,
            sotilgan=False
        ).values_list('name', flat=True).distinct()[:200]
        
        suggestions = []
        seen = set()
        
        for name in all_names:
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            
            similarity = calculate_word_similarity(query, name)
            
            # 40% dan yuqori va 100% dan past (exact emas)
            if 40 <= similarity < 100:
                suggestions.append({
                    'text': name,
                    'similarity': int(similarity)
                })
        
        # O'xshashlik bo'yicha saralash va eng yaxshi 5 tasini olish
        suggestions.sort(key=lambda x: -x['similarity'])
        
        return JsonResponse(suggestions[:5], safe=False)
        
    except Exception as e:
        print(f"api_search_suggestions xatolik: {e}")
        return JsonResponse([], safe=False)


def api_search_popular(request):
    """Ko'p qidirilgan so'zlar"""
    popular_searches = [
        "telefon", "iphone", "samsung", "xiaomi",
        "noutbuk", "macbook", "lenovo", "hp",
        "avtomobil", "mashina", "chevrolet", "damas",
        "uy", "kvartira", "ijara", "sotiladi",
        "kiyim", "shim", "ko'ylak", "kostyum",
        "mebel", "divan", "stol", "kreslo",
        "kitob", "darslik", "roman", "badiiy"
    ]
    return JsonResponse(popular_searches, safe=False)




