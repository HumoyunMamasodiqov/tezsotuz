# admin_views.py - Complete Admin Dashboard
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.urls import reverse
from datetime import timedelta

from .models import (
    Mahsulot, Sevimli, Banner, SellerProfile, PremiumUser, 
    PremiumProduct, AdminPremiumSettings, AdminAloqa, 
    PremiumRequest, PremiumNotification, Category, SotibOlish,
    BannerPurchase, FeaturedPurchase
)


def is_admin(user):
    return user.is_superuser or user.is_staff or user.groups.filter(name='Admin').exists()


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Complete admin dashboard"""
    now = timezone.now()
    
    # Stats
    total_users = User.objects.count()
    total_products = Mahsulot.objects.count()
    active_products = Mahsulot.objects.filter(aktiv=True, sotilgan=False).count()
    sold_products = Mahsulot.objects.filter(sotilgan=True).count()
    premium_products = Mahsulot.objects.filter(is_premium=True).count()
    
    # Premium stats
    premium_users = PremiumUser.objects.filter(is_premium=True).count()
    pending_requests = PremiumRequest.objects.filter(status='pending').count()
    approved_requests = PremiumRequest.objects.filter(status='approved').count()
    total_revenue = PremiumRequest.objects.filter(
        status='approved'
    ).aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
    
    # Today's stats
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_users = User.objects.filter(date_joined__gte=today_start).count()
    today_products = Mahsulot.objects.filter(sana__gte=today_start).count()
    today_requests = PremiumRequest.objects.filter(created_at__gte=today_start).count()
    
    # Recent items
    recent_products = Mahsulot.objects.order_by('-id')[:10]
    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_requests = PremiumRequest.objects.order_by('-created_at')[:10]
    
    # Expiring soon
    expiring_soon = PremiumUser.objects.filter(
        is_premium=True,
        premium_end__gte=now,
        premium_end__lte=now + timedelta(days=7)
    ).count()
    
    # Category stats
    category_stats = Mahsulot.objects.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Purchases
    purchases_count = SotibOlish.objects.count()
    recent_purchases = SotibOlish.objects.select_related('mahsulot', 'xaridor', 'sotuvchi').order_by('-created_at')[:10]
    
    # Premium products list
    recent_premium_products = PremiumProduct.objects.select_related('mahsulot', 'premium_owner').order_by('-premium_since')[:10]
    
    # Additional stats for Django admin models
    banners_count = Banner.objects.count()
    categories_count = Category.objects.count()
    sellers_count = SellerProfile.objects.count()
    favorites_count = Sevimli.objects.count()
    notifications_count = PremiumNotification.objects.count()
    premium_products_model_count = PremiumProduct.objects.count()
    admin_aloqa_count = AdminAloqa.objects.count()
    premium_settings_count = AdminPremiumSettings.objects.count()
    banner_purchases_count = BannerPurchase.objects.count()
    featured_purchases_count = FeaturedPurchase.objects.count()
    
    # Today purchases
    today_purchases = SotibOlish.objects.filter(created_at__gte=today_start).count()
    pending_purchases = SotibOlish.objects.filter(status='yangi').count()
    
    context = {
        'total_users': total_users,
        'total_products': total_products,
        'active_products': active_products,
        'sold_products': sold_products,
        'premium_products': premium_products,
        'premium_users': premium_users,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'total_revenue': total_revenue,
        'today_users': today_users,
        'today_products': today_products,
        'today_requests': today_requests,
        'recent_products': recent_products,
        'recent_users': recent_users,
        'recent_requests': recent_requests,
        'expiring_soon': expiring_soon,
        'category_stats': category_stats,
        'purchases_count': purchases_count,
        'recent_purchases': recent_purchases,
        'recent_premium_products': recent_premium_products,
        'banners_count': banners_count,
        'categories_count': categories_count,
        'sellers_count': sellers_count,
        'favorites_count': favorites_count,
        'notifications_count': notifications_count,
        'premium_products_model_count': premium_products_model_count,
        'admin_aloqa_count': admin_aloqa_count,
        'premium_settings_count': premium_settings_count,
        'today_purchases': today_purchases,
        'pending_purchases': pending_purchases,
        'banner_purchases_count': banner_purchases_count,
        'featured_purchases_count': featured_purchases_count,
    }
    return render(request, 'admin/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def admin_all_products(request):
    """View all products"""
    status = request.GET.get('status', 'all')
    category = request.GET.get('category', '')
    search = request.GET.get('q', '')
    
    products = Mahsulot.objects.all().order_by('-id')
    
    if status == 'active':
        products = products.filter(aktiv=True, sotilgan=False)
    elif status == 'sold':
        products = products.filter(sotilgan=True)
    elif status == 'premium':
        products = products.filter(is_premium=True)
    elif status == 'inactive':
        products = products.filter(aktiv=False)
    
    if category:
        products = products.filter(category=category)
    
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(user__username__icontains=search) |
            Q(tavsif__icontains=search)
        )
    
    from django.core.paginator import Paginator
    paginator = Paginator(products, 20)
    page = paginator.get_page(request.GET.get('page'))
    
    categories = dict(Mahsulot.CATEGORY_CHOICES)
    
    context = {
        'products': page,
        'page_obj': page,
        'status': status,
        'category': category,
        'search': search,
        'categories': categories,
        'total': products.count(),
    }
    return render(request, 'admin/all_products.html', context)


@login_required
@user_passes_test(is_admin)
def admin_all_users(request):
    """View all users with details"""
    search = request.GET.get('q', '')
    premium_filter = request.GET.get('premium', 'all')
    
    users = User.objects.all().order_by('-date_joined')
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    if premium_filter == 'premium':
        users = users.filter(premium_profile__is_premium=True)
    elif premium_filter == 'regular':
        users = users.filter(premium_profile__is_premium=False)
    
    user_data = []
    for u in users[:100]:
        product_count = Mahsulot.objects.filter(user=u).count()
        premium_req_count = PremiumRequest.objects.filter(user=u).count()
        is_premium = False
        try:
            is_premium = u.premium_profile.is_premium
        except:
            pass
        
        user_data.append({
            'user': u,
            'product_count': product_count,
            'premium_requests': premium_req_count,
            'is_premium': is_premium,
        })
    
    from django.core.paginator import Paginator
    paginator = Paginator(user_data, 50)
    page = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'admin/all_users.html', {
        'users': page,
        'page_obj': page,
        'search': search,
        'premium_filter': premium_filter,
        'total': len(user_data),
    })


@login_required
@user_passes_test(is_admin)
def admin_delete_product(request, product_id):
    """Admin delete product"""
    if request.method == 'POST':
        product = get_object_or_404(Mahsulot, id=product_id)
        product.delete()
        messages.success(request, f"Mahsulot o'chirildi")
    return redirect('admin_all_products')


@login_required
@user_passes_test(is_admin)
def admin_toggle_product_status(request, product_id):
    """Toggle product active status"""
    if request.method == 'POST':
        product = get_object_or_404(Mahsulot, id=product_id)
        product.aktiv = not product.aktiv
        product.save()
        messages.success(request, f"Mahsulot holati o'zgartirildi")
    return redirect('admin_all_products')


# =============================================================================
# CUSTOM HTML MODEL MANAGEMENT PAGES
# =============================================================================

@login_required
@user_passes_test(is_admin)
def admin_banners(request):
    banners = Banner.objects.all().order_by('-created_at')
    rows = [{
        'id': b.id,
        'values': [
            b.title,
            dict(Banner.DEVICE_CHOICES).get(b.device_type, b.device_type),
            'Ha' if b.is_active else "Yo'q",
            b.created_at.strftime('%d.%m.%Y %H:%M'),
        ]
    } for b in banners]
    return render(request, 'admin/model_list.html', {
        'rows': rows,
        'field_labels': ['Sarlavha', 'Qurilma', 'Faol', 'Sana'],
        'model_verbose': 'Bannerlar',
        'admin_add_url': '/admin/fronend/banner/add/',
        'admin_edit_prefix': '/admin/fronend/banner/',
    })


@login_required
@user_passes_test(is_admin)
def admin_categories(request):
    categories = Category.objects.all().order_by('-created_at')
    rows = [{
        'id': c.id,
        'values': [c.name, c.created_at.strftime('%d.%m.%Y')]
    } for c in categories]
    return render(request, 'admin/model_list.html', {
        'rows': rows,
        'field_labels': ['Nomi', 'Sana'],
        'model_verbose': 'Kategoriyalar',
        'admin_add_url': '/admin/fronend/category/add/',
        'admin_edit_prefix': '/admin/fronend/category/',
    })


@login_required
@user_passes_test(is_admin)
def admin_sellers(request):
    sellers = SellerProfile.objects.select_related('user').all().order_by('-created_at')
    rows = [{
        'id': s.id,
        'values': [
            s.user.username,
            s.phone or '-',
            f"@{s.telegram}" if s.telegram else '-',
            s.location or '-',
            'Ha' if s.is_premium_seller else "Yo'q",
            s.created_at.strftime('%d.%m.%Y'),
        ]
    } for s in sellers]
    return render(request, 'admin/model_list.html', {
        'rows': rows,
        'field_labels': ['Foydalanuvchi', 'Telefon', 'Telegram', 'Manzil', 'Premium sotuvchi', 'Sana'],
        'model_verbose': 'Sotuvchi Profillari',
        'admin_add_url': '/admin/fronend/sellerprofile/add/',
        'admin_edit_prefix': '/admin/fronend/sellerprofile/',
    })


@login_required
@user_passes_test(is_admin)
def admin_favorites(request):
    favorites = Sevimli.objects.select_related('user', 'mahsulot').all().order_by('-sana')
    rows = [{
        'id': f.id,
        'values': [
            f.user.username,
            f.mahsulot.name[:30] if f.mahsulot else '-',
            f.sana.strftime('%d.%m.%Y'),
        ]
    } for f in favorites]
    return render(request, 'admin/model_list.html', {
        'rows': rows,
        'field_labels': ['Foydalanuvchi', 'Mahsulot', 'Sana'],
        'model_verbose': 'Sevimlilar',
        'admin_add_url': '/admin/fronend/sevimli/add/',
        'admin_edit_prefix': '/admin/fronend/sevimli/',
    })


@login_required
@user_passes_test(is_admin)
def admin_notifications_list(request):
    notifications = PremiumNotification.objects.select_related('user').all().order_by('-created_at')
    rows = [{
        'id': n.id,
        'values': [
            n.user.username,
            n.title[:40],
            n.notification_type,
            'Ha' if n.is_read else "Yo'q",
            n.created_at.strftime('%d.%m.%Y %H:%M'),
        ]
    } for n in notifications]
    return render(request, 'admin/model_list.html', {
        'rows': rows,
        'field_labels': ['Foydalanuvchi', 'Sarlavha', 'Turi', "O'qilgan", 'Sana'],
        'model_verbose': 'Bildirishnomalar',
        'admin_add_url': '/admin/fronend/premiumnotification/add/',
        'admin_edit_prefix': '/admin/fronend/premiumnotification/',
    })


@login_required
@user_passes_test(is_admin)
def admin_premium_users_list(request):
    premium_users = PremiumUser.objects.select_related('user').all().order_by('-created_at')
    rows = [{
        'id': pu.id,
        'values': [
            pu.user.username,
            'Ha' if pu.is_premium else "Yo'q",
            pu.get_status_display() if hasattr(pu, 'get_status_display') else pu.status,
            pu.premium_days or 0,
            pu.premium_limit or 0,
            pu.premium_used or 0,
            pu.premium_end.strftime('%d.%m.%Y') if pu.premium_end else '-',
        ]
    } for pu in premium_users]
    return render(request, 'admin/model_list.html', {
        'rows': rows,
        'field_labels': ['Foydalanuvchi', 'Premium', 'Holati', 'Kunlar', 'Limit', 'Ishlatilgan', 'Tugash'],
        'model_verbose': 'Premium Foydalanuvchilar',
        'admin_add_url': '/admin/fronend/premiumuser/add/',
        'admin_edit_prefix': '/admin/fronend/premiumuser/',
    })


@login_required
@user_passes_test(is_admin)
def admin_contact_edit_view(request):
    """AdminAloqa ma'lumotlarini tahrirlash"""
    try:
        contact = AdminAloqa.objects.first()
    except:
        contact = None
    
    if request.method == 'POST':
        if not contact:
            contact = AdminAloqa()
        contact.manzil = request.POST.get('manzil', '')
        contact.telefon = request.POST.get('telefon', '')
        contact.email = request.POST.get('email', '')
        contact.telegram = request.POST.get('telegram', '')
        contact.instagram = request.POST.get('instagram', '')
        contact.facebook = request.POST.get('facebook', '')
        contact.save()
        messages.success(request, "Aloqa ma'lumotlari saqlandi")
        return redirect('admin_dashboard')
    
    return render(request, 'admin/admin_contact_edit.html', {
        'contact': contact,
    })


@login_required
@user_passes_test(is_admin)
def admin_premium_settings_view(request):
    """Premium sozlamalarini tahrirlash"""
    settings = AdminPremiumSettings.get_settings()

    if request.method == 'POST':
        settings.premium_fee_amount = request.POST.get('premium_fee_amount') or settings.premium_fee_amount
        settings.premium_per_day_price = request.POST.get('premium_per_day_price') or settings.premium_per_day_price
        settings.premium_per_week_price = request.POST.get('premium_per_week_price') or settings.premium_per_week_price
        settings.premium_per_month_price = request.POST.get('premium_per_month_price') or settings.premium_per_month_price
        settings.premium_per_3months_price = request.POST.get('premium_per_3months_price') or settings.premium_per_3months_price
        settings.premium_per_6months_price = request.POST.get('premium_per_6months_price') or settings.premium_per_6months_price
        settings.premium_per_year_price = request.POST.get('premium_per_year_price') or settings.premium_per_year_price
        settings.has_discount = request.POST.get('has_discount') == 'on'
        settings.discount_percentage = request.POST.get('discount_percentage') or settings.discount_percentage
        discount_end_date = request.POST.get('discount_end_date')
        settings.discount_end_date = discount_end_date if discount_end_date else None
        settings.is_premium_enabled = request.POST.get('is_premium_enabled') == 'on'
        settings.max_premium_products = request.POST.get('max_premium_products') or settings.max_premium_products
        settings.premium_duration_days = request.POST.get('premium_duration_days') or settings.premium_duration_days
        settings.auto_approve_premium = request.POST.get('auto_approve_premium') == 'on'
        settings.auto_renew_premium = request.POST.get('auto_renew_premium') == 'on'
        settings.require_admin_approval = request.POST.get('require_admin_approval') == 'on'
        settings.max_premium_requests_per_user = request.POST.get('max_premium_requests_per_user') or settings.max_premium_requests_per_user
        settings.premium_request_expiry_days = request.POST.get('premium_request_expiry_days') or settings.premium_request_expiry_days
        settings.notify_before_days = request.POST.get('notify_before_days') or settings.notify_before_days
        settings.admin_contact_phone = request.POST.get('admin_contact_phone') or settings.admin_contact_phone
        settings.admin_contact_telegram = request.POST.get('admin_contact_telegram') or settings.admin_contact_telegram
        settings.admin_contact_email = request.POST.get('admin_contact_email') or settings.admin_contact_email
        settings.payment_methods = request.POST.get('payment_methods') or settings.payment_methods
        settings.bank_card_number = request.POST.get('bank_card_number') or settings.bank_card_number
        settings.bank_name = request.POST.get('bank_name') or settings.bank_name
        settings.bank_card_owner = request.POST.get('bank_card_owner') or settings.bank_card_owner
        settings.banner_price_per_day = request.POST.get('banner_price_per_day') or settings.banner_price_per_day
        settings.featured_price_per_day = request.POST.get('featured_price_per_day') or settings.featured_price_per_day
        settings.save()
        messages.success(request, "Premium sozlamalari saqlandi")
        return redirect('admin_dashboard')

    return render(request, 'admin/premium_settings.html', {
        'settings': settings,
    })
