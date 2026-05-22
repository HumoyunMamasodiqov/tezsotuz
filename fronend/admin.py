from django.contrib import admin
from django.contrib.auth.models import User  
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.html import format_html
from django.db.models import Q, Count, Sum
import json

from .models import (
    Banner, Mahsulot, Sevimli, Category, SellerProfile, AdminAloqa,
    PremiumUser, PremiumProduct, AdminPremiumSettings, PremiumRequest, 
    PremiumNotification
)



@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'device_type', 'is_active', 'created_at']
    list_filter = ['device_type', 'is_active', 'created_at']
    search_fields = ['title']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Asosiy maʼlumotlar', {
            'fields': ('title', 'image', 'device_type', 'link', 'is_active')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-created_at')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    list_filter = ['created_at']


@admin.register(Mahsulot)
class MahsulotAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'narx_formatted', 'viloyat', 'sana', 
                   'sotilgan_ha_yoq', 'aktiv', 'is_premium', 'premium_status_display']
    list_filter = ['category', 'viloyat', 'sotilgan', 'aktiv', 'is_premium', 'sana']
    search_fields = ['name', 'tavsif', 'category', 'mahsulotturi']
    date_hierarchy = 'sana'
    readonly_fields = ['korishlar_soni', 'premium_views']
    list_per_page = 20
    
    def narx_formatted(self, obj):
        return obj.narx_formatted()
    narx_formatted.short_description = 'Narx'
    
    def sotilgan_ha_yoq(self, obj):
        return obj.sotilgan_ha_yoq()
    sotilgan_ha_yoq.short_description = 'Holati'
    
    def premium_status_display(self, obj):
        return obj.get_premium_status_display()
    premium_status_display.short_description = 'Premium Holati'


@admin.register(Sevimli)
class SevimliAdmin(admin.ModelAdmin):
    list_display = ['user', 'mahsulot', 'sana']
    list_filter = ['sana']
    search_fields = ['user__username', 'mahsulot__name']


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'telegram', 'location', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone', 'location', 'instagram', 'telegram']
    list_filter = ['created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Asosiy maʼlumotlar', {
            'fields': ('user', 'bio', 'location', 'phone')
        }),
        ('Ijtimoiy tarmoqlar', {
            'fields': ('instagram', 'telegram')
        }),
        ('Ish vaqti', {
            'fields': ('work_hours_start', 'work_hours_end')
        }),
        ('Rasmlar', {
            'fields': ('profile_image', 'banner_image')
        }),
        ('Tarix', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(AdminAloqa)
class AdminAloqaAdmin(admin.ModelAdmin):
    list_display = ['manzil', 'telefon', 'email', 'telegram', 'instagram', 'facebook']
    
    def has_add_permission(self, request):
        return not AdminAloqa.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PremiumUser)
class PremiumUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_premium', 'status', 'premium_start', 'premium_end', 
                   'admin_approved', 'premium_limit', 'premium_used', 'days_remaining', 'created_at']
    list_filter = ['is_premium', 'status', 'admin_approved', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 20
    actions = ['approve_premium', 'reject_premium', 'extend_premium', 'deactivate_premium', 
               'reset_counter', 'manual_activate_premium']
    
    def days_remaining(self, obj):
        return obj.get_days_remaining()
    days_remaining.short_description = 'Qolgan kunlar'
    
    def approve_premium(self, request, queryset):
        count = 0
        for premium_user in queryset:
            if not premium_user.is_premium:
                premium_user.activate_premium(days=30, admin_user=request.user)
                count += 1
        
        if count > 0:
            self.message_user(request, f"{count} ta foydalanuvchi premium tasdiqlandi")
        else:
            self.message_user(request, "Hech qanday foydalanuvchi tasdiqlanmadi", level=messages.WARNING)
    approve_premium.short_description = "Tanlangan premium'ni tasdiqlash"
    
    def manual_activate_premium(self, request, queryset):
        count = 0
        for premium_user in queryset:
            if not premium_user.is_premium:
                now = timezone.now()
                premium_user.is_premium = True
                premium_user.status = 'active'
                premium_user.admin_approved = True
                premium_user.premium_start = now
                premium_user.premium_end = now + timedelta(days=30)
                premium_user.premium_days = 30
                premium_user.premium_used = 0
                premium_user.request_premium_access = False
                premium_user.notified_before_expiry = False
                premium_user.last_check = now
                premium_user.save()
                
                try:
                    seller_profile = SellerProfile.objects.get(user=premium_user.user)
                    seller_profile.is_premium_seller = True
                    seller_profile.premium_seller_since = now
                    seller_profile.save()
                except:
                    pass
                
                count += 1
        
        if count > 0:
            self.message_user(request, f"{count} ta foydalanuvchi premium faollashtirildi")
    manual_activate_premium.short_description = "Qo'lda premium faollashtirish"
    
    def reject_premium(self, request, queryset):
        count = 0
        for premium_user in queryset:
            if premium_user.is_premium:
                premium_user.reject_premium("Admin tomonidan rad etildi")
                count += 1
        self.message_user(request, f"{count} ta premium rad etildi")
    reject_premium.short_description = "Tanlangan premium'ni rad etish"
    
    def extend_premium(self, request, queryset):
        count = 0
        for premium_user in queryset:
            if premium_user.is_premium and premium_user.premium_end:
                premium_user.premium_end = premium_user.premium_end + timedelta(days=30)
                premium_user.premium_days += 30
                premium_user.save()
                count += 1
        self.message_user(request, f"{count} ta premium 30 kunga uzaytirildi")
    extend_premium.short_description = "Premium muddatini 30 kunga uzaytirish"
    
    def deactivate_premium(self, request, queryset):
        count = 0
        for premium_user in queryset:
            if premium_user.is_premium:
                premium_user.deactivate_premium()
                count += 1
        self.message_user(request, f"{count} ta premium deaktivlashtirildi")
    deactivate_premium.short_description = "Premium'ni deaktivlashtirish"
    
    def reset_counter(self, request, queryset):
        count = 0
        for premium_user in queryset:
            premium_user.reset_premium_counter()
            count += 1
        self.message_user(request, f"{count} ta premium counter yangilandi")
    reset_counter.short_description = "Premium counter ni qayta hisoblash"


@admin.register(PremiumRequest)
class PremiumRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'full_name', 'phone', 'status', 'payment_status',
                   'requested_days', 'requested_limit', 'calculated_total', 
                   'created_at', 'admin_user']
    
    list_filter = ['status', 'payment_status', 'created_at', 'admin_user', 
                  'requested_days', 'payment_method']
    
    search_fields = ['id', 'full_name', 'user__username', 'phone', 'email',
                    'transaction_id', 'admin_notes']
    
    readonly_fields = ['created_at', 'updated_at', 'approved_at', 'expired_at',
                      'cancelled_at', 'payment_date']
    
    list_editable = ['status', 'payment_status']
    list_per_page = 50
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    actions = ['approve_selected', 'reject_selected', 'mark_as_expired',
              'mark_payment_completed', 'mark_payment_failed', 'export_to_csv',
              'send_notification']
    
    fieldsets = (
        ('Asosiy maʼlumotlar', {
            'fields': ('user', 'full_name', 'phone', 'telegram_username', 'email')
        }),
        ('Premium sozlamalar', {
            'fields': ('requested_days', 'requested_limit', 'calculated_total')
        }),
        ('Toʻlov maʼlumotlari', {
            'fields': ('payment_status', 'payment_method', 'payment_amount',
                      'transaction_id', 'payment_proof', 'payment_date')
        }),
        ('Status va izohlar', {
            'fields': ('status', 'notes', 'admin_notes', 'rejection_reason',
                      'admin_user', 'approved_by', 'approved_at')
        }),
        ('Qoʻshimcha sozlamalar', {
            'fields': ('auto_approve', 'notification_sent', 'viewed_by_admin',
                      'priority', 'ip_address', 'user_agent')
        }),
        ('Tarix', {
            'fields': ('created_at', 'updated_at', 'expired_at', 'cancelled_at')
        }),
    )
    
    def approve_selected(self, request, queryset):
        count = 0
        failed = 0
        
        for req in queryset.filter(status='pending'):
            try:
                success = req.approve(request.user)
                if success:
                    count += 1
                else:
                    failed += 1
            except Exception as e:
                self.message_user(request, f"So'rov {req.id} xatosi: {str(e)}", level=messages.ERROR)
                failed += 1
        
        if count > 0:
            self.message_user(request, f"{count} ta so'rov tasdiqlandi")
        if failed > 0:
            self.message_user(request, f"{failed} ta so'rovda xatolik yuz berdi", level=messages.WARNING)
    approve_selected.short_description = "Tanlangan so'rovlarni tasdiqlash"
    
    def reject_selected(self, request, queryset):
        count = 0
        for req in queryset.filter(status='pending'):
            req.reject(request.user, 'Admin tomonidan rad etildi')
            count += 1
        self.message_user(request, f"{count} ta so'rov rad etildi")
    reject_selected.short_description = "Tanlangan so'rovlarni rad etish"
    
    def mark_as_expired(self, request, queryset):
        count = 0
        for req in queryset.filter(status='pending'):
            if req.is_expired():
                req.mark_as_expired()
                count += 1
        self.message_user(request, f"{count} ta so'rov muddati o'tgan deb belgilandi")
    mark_as_expired.short_description = "Tanlangan so'rovlarni muddati o'tgan qilish"
    
    def mark_payment_completed(self, request, queryset):
        count = 0
        for req in queryset.filter(payment_status__in=['pending', 'processing']):
            req.payment_status = 'completed'
            req.payment_date = timezone.now()
            req.save()
            count += 1
        self.message_user(request, f"{count} ta to'lov tasdiqlandi")
    mark_payment_completed.short_description = "To'lovni tasdiqlash"
    
    def mark_payment_failed(self, request, queryset):
        count = 0
        for req in queryset.filter(payment_status__in=['pending', 'processing']):
            req.payment_status = 'failed'
            req.save()
            count += 1
        self.message_user(request, f"{count} ta to'lov muvaffaqiyatsiz deb belgilandi")
    mark_payment_failed.short_description = "To'lovni muvaffaqiyatsiz qilish"
    
    def export_to_csv(self, request, queryset):
        import csv
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="premium_requests.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Foydalanuvchi', 'Toʻliq ism', 'Telefon', 'Email',
            'Kunlar', 'Limit', 'Summa', 'Toʻlov holati', 'Holati',
            'Yaratilgan sana', 'Tasdiqlangan sana', 'Admin'
        ])
        
        for req in queryset:
            writer.writerow([
                req.id, req.user.username, req.full_name, req.phone,
                req.email or '', req.requested_days, req.requested_limit,
                req.calculated_total, req.get_payment_status_display(),
                req.get_status_display(), req.created_at.strftime('%Y-%m-%d %H:%M'),
                req.approved_at.strftime('%Y-%m-%d %H:%M') if req.approved_at else '',
                req.admin_user.username if req.admin_user else ''
            ])
        
        return response
    export_to_csv.short_description = "CSV formatida eksport qilish"
    
    def send_notification(self, request, queryset):
        count = 0
        for req in queryset:
            try:
                req.send_notification(
                    title="Premium So'rovingiz yangilandi",
                    message=f"Sizning #{req.id} raqamli so'rovingiz yangilandi. Holati: {req.get_status_display()}",
                    notification_type='admin_notification'
                )
                count += 1
            except:
                pass
        
        self.message_user(request, f"{count} ta foydalanuvchiga bildirishnoma yuborildi")
    send_notification.short_description = "Tanlanganlarga bildirishnoma yuborish"
    
    def has_add_permission(self, request):
        return False


@admin.register(PremiumProduct)
class PremiumProductAdmin(admin.ModelAdmin):
    list_display = ['mahsulot', 'premium_owner', 'admin_approved', 'is_active', 
                   'premium_since', 'premium_until', 'days_left']
    list_filter = ['admin_approved', 'is_active', 'premium_since']
    search_fields = ['mahsulot__name', 'premium_owner__username']
    readonly_fields = ['premium_since', 'approval_date']
    actions = ['approve_products', 'reject_products', 'deactivate_products']
    
    def days_left(self, obj):
        if obj.premium_until:
            days = (obj.premium_until - timezone.now()).days
            return max(0, days)
        return 0
    days_left.short_description = 'Qolgan kunlar'
    
    def approve_products(self, request, queryset):
        count = 0
        for product in queryset:
            if not product.admin_approved:
                product.approve_premium(request.user)
                count += 1
        self.message_user(request, f"{count} ta mahsulot premium tasdiqlandi")
    approve_products.short_description = "Tanlangan mahsulotlarni tasdiqlash"
    
    def reject_products(self, request, queryset):
        count = 0
        for product in queryset:
            if product.admin_approved:
                product.admin_approved = False
                product.is_active = False
                product.save()
                count += 1
        self.message_user(request, f"{count} ta mahsulot premiumdan olib tashlandi")
    reject_products.short_description = "Tanlangan mahsulotlarni premiumdan olib tashlash"
    
    def deactivate_products(self, request, queryset):
        count = 0
        for product in queryset:
            if product.is_active:
                product.is_active = False
                product.save()
                product.mahsulot.deactivate_premium()
                count += 1
        self.message_user(request, f"{count} ta mahsulot deaktivlashtirildi")
    deactivate_products.short_description = "Tanlangan mahsulotlarni deaktivlashtirish"


@admin.register(PremiumNotification)
class PremiumNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at']
    list_per_page = 20
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        count = queryset.update(is_read=True)
        self.message_user(request, f"{count} ta bildirishnoma o'qilgan qilindi")
    mark_as_read.short_description = "Tanlangan bildirishnomalarni o'qilgan qilish"
    
    def mark_as_unread(self, request, queryset):
        count = queryset.update(is_read=False)
        self.message_user(request, f"{count} ta bildirishnoma o'qilmagan qilindi")
    mark_as_unread.short_description = "Tanlangan bildirishnomalarni o'qilmagan qilish"

from django.contrib import admin
from django.utils.html import format_html
import json

@admin.register(AdminPremiumSettings)
class AdminPremiumSettingsAdmin(admin.ModelAdmin):
    """Premium sozlamalar - JSON formatli to'lov usullari bilan"""
    
    list_display = ['premium_fee_amount', 'premium_per_day_price', 'has_discount', 'is_premium_enabled']
    
    fieldsets = (
        ('Premium Narxlar', {
            'fields': (
                ('premium_fee_amount', 'premium_per_day_price'),
                ('premium_per_week_price', 'premium_per_month_price'),
                ('premium_per_3months_price', 'premium_per_6months_price'),
                'premium_per_year_price',
            )
        }),
        
        ('Chegirma', {
            'fields': ('has_discount', 'discount_percentage', 'discount_end_date')
        }),
        
        ('To\'lov Usullari - JSON', {
            'fields': ('payment_methods_json',),
            'description': 'To\'lov usullarini JSON formatida boshqaring. Misol: [{"name": "HUMO", "icon": "credit-card", "active": true}]'
        }),
        
        ('Bank Kartalari - JSON', {
            'fields': ('bank_cards_json',),
            'description': 'Bank kartalarini JSON formatida boshqaring. Misol: [{"card_number": "8600 1234 5678 9012", "card_owner": "TEZ SOT", "bank_name": "HUMO", "card_type": "humo", "active": true}]'
        }),
        
        ('Aloqa Ma\'lumotlari', {
            'fields': ('admin_contact_phone', 'admin_contact_telegram', 'admin_contact_email')
        }),
        
        ('Asosiy Sozlamalar', {
            'fields': (
                'is_premium_enabled', 
                'max_premium_products', 
                'max_premium_requests_per_user',
                'premium_duration_days',
                'auto_approve_premium',
                'auto_renew_premium',
                'require_admin_approval',
                'premium_request_expiry_days',
                'notify_before_days'
            )
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Model saqlanganda JSON validatsiya"""
        
        # Payment methods validatsiya
        if obj.payment_methods_json:
            try:
                if isinstance(obj.payment_methods_json, str):
                    obj.payment_methods_json = json.loads(obj.payment_methods_json)
                
                for method in obj.payment_methods_json:
                    if not isinstance(method, dict):
                        raise ValueError("Har bir to'lov usuli dict bo'lishi kerak")
                    if 'name' not in method:
                        raise ValueError("Har bir to'lov usulida 'name' bo'lishi kerak")
                    
                    method.setdefault('icon', 'credit-card')
                    method.setdefault('active', True)
                
            except (json.JSONDecodeError, ValueError) as e:
                self.message_user(request, f"To'lov usullari JSON xatosi: {str(e)}", level='ERROR')
                return
        
        # Bank cards validatsiya
        if obj.bank_cards_json:
            try:
                if isinstance(obj.bank_cards_json, str):
                    obj.bank_cards_json = json.loads(obj.bank_cards_json)
                
                for card in obj.bank_cards_json:
                    if not isinstance(card, dict):
                        raise ValueError("Har bir karta dict bo'lishi kerak")
                    
                    required_fields = ['card_number', 'card_owner', 'bank_name']
                    for field in required_fields:
                        if field not in card:
                            raise ValueError(f"Kartada '{field}' bo'lishi kerak")
                    
                    card.setdefault('card_type', 'humo')
                    card.setdefault('active', True)
                
            except (json.JSONDecodeError, ValueError) as e:
                self.message_user(request, f"Bank kartalari JSON xatosi: {str(e)}", level='ERROR')
                return
        
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        return not AdminPremiumSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False