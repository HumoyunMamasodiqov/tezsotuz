from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone

from .models import Mahsulot, SotibOlish, PremiumNotification, PremiumRequest, PremiumUser, AdminPremiumSettings, BannerPurchase, FeaturedPurchase, SellerProfile


CART_SESSION_KEY = 'savat'


def _get_cart(request):
    if CART_SESSION_KEY not in request.session:
        request.session[CART_SESSION_KEY] = {}
    return request.session[CART_SESSION_KEY]


def _save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


@login_required
def add_to_cart(request, mahsulot_id):
    mahsulot = get_object_or_404(Mahsulot, id=mahsulot_id)
    if mahsulot.user == request.user:
        messages.warning(request, "O'z mahsulotingizni savatga qo'sha olmaysiz")
        return redirect('mahsulot_detail', mahsulot_id=mahsulot_id)
    if mahsulot.sotilgan:
        messages.warning(request, "Bu mahsulot allaqachon sotilgan")
        return redirect('mahsulot_detail', mahsulot_id=mahsulot_id)

    cart = _get_cart(request)
    key = str(mahsulot_id)
    if key in cart:
        cart[key]['miqdor'] = cart[key]['miqdor'] + 1
        messages.info(request, f"{mahsulot.name} savatda soni oshirildi")
    else:
        cart[key] = {'miqdor': 1, 'qoshilgan': timezone.now().isoformat()}
        messages.success(request, f"{mahsulot.name} savatga qo'shildi")
    _save_cart(request, cart)

    next_url = request.GET.get('next', 'mahsulot_detail')
    if next_url == 'mahsulot_detail':
        return redirect('mahsulot_detail', mahsulot_id=mahsulot_id)
    return redirect('view_cart')


@login_required
def view_cart(request):
    cart = _get_cart(request)
    items = []
    total = 0
    for pid, data in cart.items():
        try:
            p = Mahsulot.objects.get(id=int(pid))
            narx_int = int(float(str(p.narx).replace(',', '').replace(' ', ''))) if p.narx else 0
            item_total = narx_int * data['miqdor']
            total += item_total
            items.append({
                'mahsulot': p,
                'miqdor': data['miqdor'],
                'narx': narx_int,
                'jami': item_total,
            })
        except (Mahsulot.DoesNotExist, ValueError):
            pass
    return render(request, 'savat.html', {'items': items, 'total': total})


@login_required
def remove_from_cart(request, mahsulot_id):
    cart = _get_cart(request)
    key = str(mahsulot_id)
    if key in cart:
        del cart[key]
        _save_cart(request, cart)
        messages.success(request, "Mahsulot savatdan olib tashlandi")
    return redirect('view_cart')


@login_required
def update_cart(request, mahsulot_id):
    if request.method == 'POST':
        miqdor = int(request.POST.get('miqdor', 1))
        if miqdor < 1:
            miqdor = 1
        cart = _get_cart(request)
        key = str(mahsulot_id)
        if key in cart:
            cart[key]['miqdor'] = miqdor
            _save_cart(request, cart)
            messages.success(request, "Savat yangilandi")
    return redirect('view_cart')


@login_required
def checkout(request):
    cart = _get_cart(request)
    if not cart:
        messages.warning(request, "Savatingiz bo'sh")
        return redirect('view_cart')

    if request.method == 'POST':
        ism = request.POST.get('ism', '').strip()
        telefon = request.POST.get('telefon', '').strip()
        manzil = request.POST.get('manzil', '').strip()
        izoh = request.POST.get('izoh', '').strip()

        errors = []
        if not ism:
            errors.append("Iltimos, ismingizni kiriting")
        if not telefon:
            errors.append("Iltimos, telefon raqamingizni kiriting")
        if not manzil:
            errors.append("Iltimos, yetkazib berish manzilini kiriting")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'checkout.html', {
                'cart_items': cart,
                'ism': ism,
                'telefon': telefon,
                'manzil': manzil,
                'izoh': izoh,
            })

        purchases = []
        for pid, data in cart.items():
            try:
                p = Mahsulot.objects.get(id=int(pid))
            except Mahsulot.DoesNotExist:
                continue

            if p.sotilgan:
                messages.warning(request, f"'{p.name}' allaqachon sotilgan")
                continue

            jami = 0
            try:
                narx_int = int(float(str(p.narx).replace(',', '').replace(' ', '')))
                jami = str(narx_int * data['miqdor'])
            except:
                jami = p.narx

            sotib = SotibOlish.objects.create(
                mahsulot=p,
                xaridor=request.user,
                sotuvchi=p.user,
                miqdor=data['miqdor'],
                narx=p.narx,
                jami_narx=jami,
                xaridor_ism=ism,
                xaridor_telefon=telefon,
                xaridor_manzil=manzil,
                xaridor_izoh=izoh,
            )
            p.sotilgan = True
            p.save()
            purchases.append(sotib)

        request.session[CART_SESSION_KEY] = {}
        request.session.modified = True

        if purchases:
            _send_purchase_notifications(purchases, request.user)
            messages.success(request, f"Buyurtmangiz qabul qilindi! {len(purchases)} ta mahsulot sotib olindi")
        return redirect('my_purchases')

    items = []
    total = 0
    for pid, data in cart.items():
        try:
            p = Mahsulot.objects.get(id=int(pid))
            narx_int = int(float(str(p.narx).replace(',', '').replace(' ', ''))) if p.narx else 0
            item_total = narx_int * data['miqdor']
            total += item_total
            items.append({'mahsulot': p, 'miqdor': data['miqdor'], 'jami': item_total})
        except:
            pass
    return render(request, 'checkout.html', {'items': items, 'total': total})


def _send_purchase_notifications(purchases, xaridor):
    for sotib in purchases:
        PremiumNotification.objects.create(
            user=sotib.sotuvchi,
            notification_type='new_request',
            title="Yangi buyurtma!",
            message=f"#{sotib.id} - {sotib.mahsulot.name} mahsulotingiz sotib olindi. Xaridor: {sotib.xaridor_ism} ({sotib.xaridor_telefon})",
            data={'purchase_id': sotib.id, 'type': 'purchase'}
        )
        for admin in User.objects.filter(is_superuser=True):
            PremiumNotification.objects.create(
                user=admin,
                notification_type='new_request',
                title="Yangi buyurtma!",
                message=f"#{sotib.id} - {sotib.mahsulot.name} mahsulot sotib olindi. Xaridor: {sotib.xaridor_ism}, Sotuvchi: {sotib.sotuvchi.username}",
                data={'purchase_id': sotib.id, 'type': 'purchase'}
            )


@login_required
def my_purchases(request):
    purchases = SotibOlish.objects.filter(xaridor=request.user).select_related('mahsulot', 'sotuvchi').order_by('-created_at')
    return render(request, 'mening_xaridlarim.html', {'purchases': purchases})


@login_required
def my_sales(request):
    purchases = SotibOlish.objects.filter(sotuvchi=request.user).select_related('mahsulot', 'xaridor').order_by('-created_at')
    for p in purchases:
        p.read_by_seller = True
        p.save(update_fields=['read_by_seller'])
    return render(request, 'sotuvlarim.html', {'purchases': purchases, 'status_choices': SotibOlish.STATUS_CHOICES})


@login_required
def update_purchase_status(request, purchase_id):
    if request.method == 'POST':
        sotib = get_object_or_404(SotibOlish, id=purchase_id)
        if sotib.sotuvchi != request.user and not request.user.is_superuser:
            messages.error(request, "Siz bu buyurtmani o'zgartira olmaysiz")
            return redirect('my_sales')
        new_status = request.POST.get('status', '')
        if new_status in dict(SotibOlish.STATUS_CHOICES):
            sotib.status = new_status
            sotib.save()
            messages.success(request, f"Buyurtma holati yangilandi: {sotib.get_status_display()}")
    return redirect('my_sales')


@login_required
def cancel_purchase(request, purchase_id):
    sotib = get_object_or_404(SotibOlish, id=purchase_id, xaridor=request.user)
    if sotib.status == 'yangi':
        sotib.status = 'bekor_qilindi'
        sotib.save()
        sotib.mahsulot.sotilgan = False
        sotib.mahsulot.save()
        messages.success(request, "Buyurtma bekor qilindi")
    else:
        messages.error(request, "Bu buyurtmani bekor qilib bo'lmaydi")
    return redirect('my_purchases')


# =============================================================================
# PREMIUM SUBSCRIPTION PURCHASE
# =============================================================================

@login_required
def buy_premium_view(request):
    """Premium obuna sotib olish"""
    settings = AdminPremiumSettings.get_settings()
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        requested_days = int(request.POST.get('requested_days', 30))
        payment_method = request.POST.get('payment_method', '')
        payment_proof = request.FILES.get('payment_proof')
        
        if not full_name or not phone:
            messages.error(request, "Ism va telefon majburiy")
            return redirect('buy_premium')
        
        if not payment_proof:
            messages.error(request, "To'lov chekini yuklash majburiy")
            return redirect('buy_premium')
        
        from decimal import Decimal
        if requested_days == 7:
            price = settings.premium_per_week_price or Decimal('12000')
        elif requested_days == 30:
            price = settings.premium_per_month_price or Decimal('60000')
        elif requested_days == 90:
            price = settings.premium_per_3months_price or Decimal('150000')
        elif requested_days == 365:
            price = settings.premium_per_year_price or Decimal('500000')
        else:
            price = (settings.premium_per_day_price or Decimal('2000')) * requested_days
        
        import re
        cleaned_phone = re.sub(r'\D', '', phone)
        
        req_limit = int(settings.max_premium_products or 5)
        if req_limit < 1: req_limit = 1
        if req_limit > 50: req_limit = 50
        
        premium_request = PremiumRequest.objects.create(
            user=request.user,
            full_name=full_name,
            phone=cleaned_phone,
            requested_days=requested_days,
            requested_limit=req_limit,
            payment_amount=price,
            calculated_total=price,
            payment_method=payment_method,
            payment_proof=payment_proof,
            status='pending',
            payment_status='pending',
        )
        
        messages.success(request, f"Premium so'rovingiz yuborildi! Admin tasdiqlashini kuting.")
        return redirect('my_premium_requests')
    
    return render(request, 'buy_premium.html', {
        'settings': settings,
        'payment_methods': ['Bank karta', 'Click', 'Payme', 'Uzumbank'],
    })


# =============================================================================
# BANNER PURCHASE
# =============================================================================

@login_required
def buy_banner_view(request):
    """Banner joyini sotib olish"""
    settings = AdminPremiumSettings.get_settings()
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        link = request.POST.get('link', '')
        device_type = request.POST.get('device_type', 'desktop')
        days = int(request.POST.get('days', 30))
        image = request.FILES.get('image')
        payment_proof = request.FILES.get('payment_proof')
        
        if not title or not image:
            messages.error(request, "Sarlavha va rasm majburiy")
            return redirect('buy_banner')
        
        if not payment_proof:
            messages.error(request, "To'lov chekini yuklash majburiy")
            return redirect('buy_banner')
        
        from decimal import Decimal
        price_per_day = float(settings.banner_price_per_day or 5000)
        price = Decimal(str(price_per_day * days))
        
        banner_purchase = BannerPurchase.objects.create(
            user=request.user,
            title=title,
            image=image,
            link=link,
            device_type=device_type,
            days=days,
            price=price,
            payment_proof=payment_proof,
            status='kutilmoqda',
        )
        
        messages.success(request, f"Banner so'rovingiz yuborildi! Admin tasdiqlashini kuting.")
        return redirect('my_profile')
    
    return render(request, 'buy_banner.html', {
        'settings': settings,
        'price_per_day': int(settings.banner_price_per_day or 5000),
        'price_7_days': int((settings.banner_price_per_day or 5000) * 7),
        'price_30_days': int((settings.banner_price_per_day or 5000) * 30),
        'price_90_days': int((settings.banner_price_per_day or 5000) * 90),
    })


# =============================================================================
# FEATURED/TOP PRODUCT PURCHASE
# =============================================================================

@login_required
def buy_featured_view(request, product_id):
    """Mahsulotni featured qilish (egalari va xaridorlar uchun)"""
    mahsulot = get_object_or_404(Mahsulot, id=product_id)
    
    # Faqat mahsulot egasi yoki uni sotib olganlar featured qila oladi
    is_owner = mahsulot.user == request.user
    is_buyer = SotibOlish.objects.filter(mahsulot=mahsulot, xaridor=request.user).exists()
    
    if not is_owner and not is_buyer:
        messages.error(request, "Siz bu mahsulotni featured qila olmaysiz")
        return redirect('home')
    
    settings = AdminPremiumSettings.get_settings()
    
    if request.method == 'POST':
        days = int(request.POST.get('days', 7))
        payment_proof = request.FILES.get('payment_proof')
        
        if not payment_proof:
            messages.error(request, "To'lov chekini yuklash majburiy")
            return redirect('buy_featured', product_id=product_id)
        
        from decimal import Decimal
        price_per_day = float(settings.featured_price_per_day or 3000)
        price = Decimal(str(price_per_day * days))
        
        featured = FeaturedPurchase.objects.create(
            user=request.user,
            mahsulot=mahsulot,
            days=days,
            price=price,
            payment_proof=payment_proof,
            status='kutilmoqda',
        )
        
        messages.success(request, f"Top mahsulot so'rovingiz yuborildi! Admin tasdiqlashini kuting.")
        return redirect('my_profile')
    
    return render(request, 'buy_featured.html', {
        'mahsulot': mahsulot,
        'settings': settings,
        'price_per_day': int(settings.featured_price_per_day or 3000),
        'price_7_days': int((settings.featured_price_per_day or 3000) * 7),
        'price_14_days': int((settings.featured_price_per_day or 3000) * 14),
        'price_30_days': int((settings.featured_price_per_day or 3000) * 30),
        'price_90_days': int((settings.featured_price_per_day or 3000) * 90),
    })


# =============================================================================
# ADMIN - MANAGE BANNER PURCHASES
# =============================================================================

@login_required
def admin_banner_purchases(request):
    if not request.user.is_superuser:
        return redirect('home')
    purchases = BannerPurchase.objects.all().order_by('-created_at')
    return render(request, 'admin/banner_purchases.html', {'purchases': purchases})


@login_required
def admin_banner_approve(request, purchase_id):
    if not request.user.is_superuser:
        return redirect('home')
    purchase = get_object_or_404(BannerPurchase, id=purchase_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            purchase.approve()
            messages.success(request, "Banner tasdiqlandi")
        elif action == 'reject':
            purchase.status = 'bekor_qilindi'
            purchase.save()
            messages.success(request, "Banner rad etildi")
    return redirect('admin_banner_purchases')


# =============================================================================
# ADMIN - MANAGE FEATURED PURCHASES
# =============================================================================

@login_required
def admin_featured_purchases(request):
    if not request.user.is_superuser:
        return redirect('home')
    purchases = FeaturedPurchase.objects.all().order_by('-created_at')
    return render(request, 'admin/featured_purchases.html', {'purchases': purchases})


@login_required 
def admin_featured_approve(request, purchase_id):
    if not request.user.is_superuser:
        return redirect('home')
    purchase = get_object_or_404(FeaturedPurchase, id=purchase_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            purchase.approve()
            messages.success(request, "Top mahsulot tasdiqlandi")
        elif action == 'reject':
            purchase.status = 'bekor_qilindi'
            purchase.save()
            messages.success(request, "Top mahsulot rad etildi")
    return redirect('admin_featured_purchases')


# =============================================================================
# USER PRODUCT SELECTION FOR FEATURED
# =============================================================================

@login_required
def select_product_for_featured(request):
    """TOP qilish uchun mahsulot tanlash (egalari va xaridorlar uchun)"""
    owned_products = Mahsulot.objects.filter(user=request.user, aktiv=True)
    purchased_ids = SotibOlish.objects.filter(
        xaridor=request.user
    ).values_list('mahsulot_id', flat=True).distinct()
    purchased_products = Mahsulot.objects.filter(id__in=purchased_ids, aktiv=True)
    
    from itertools import chain
    products = list(chain(owned_products, purchased_products))
    seen = set()
    unique_products = []
    for p in products:
        if p.id not in seen:
            seen.add(p.id)
            unique_products.append(p)
    
    return render(request, 'select_product_for_featured.html', {
        'products': unique_products,
    })
