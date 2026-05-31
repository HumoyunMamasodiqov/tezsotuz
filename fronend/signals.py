# fronend/signals.py
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from django.contrib.auth.models import User
from .models import (
    SellerProfile, PremiumUser, PremiumRequest, Mahsulot, 
    PremiumProduct, PremiumNotification, AdminPremiumSettings
)

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
    except Exception as e:
        print(f"[create_admin_notification] Error: {e}")


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
    except Exception as e:
        print(f"[create_user_notification] Error for {user.username}: {e}")


@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    """Yangi user yaratilganda avtomatik profillar yaratish"""
    if created:
        # SellerProfile yaratish
        SellerProfile.objects.get_or_create(user=instance)
        
        # PremiumUser yaratish (faqat yaratish, premium emas)
        PremiumUser.objects.get_or_create(user=instance)


@receiver(post_save, sender=PremiumRequest)
def notify_admin_on_premium_request(sender, instance, created, **kwargs):
    """Yangi premium so'rov yaratilganda adminlarga bildirishnoma yuborish"""
    if created:
        try:
            settings = AdminPremiumSettings.get_settings()
            if settings.send_notifications:
                # Adminlarga bildirishnoma yaratish
                create_admin_notification(
                    title="Yangi Premium So'rovi",
                    message=f"{instance.user.username} yangi premium so'rovi yubordi",
                    data={
                        'request_id': instance.id,
                        'user_id': instance.user.id,
                        'full_name': instance.full_name,
                        'phone': instance.phone
                    }
                )
        except Exception as e:
            print(f"[PremiumRequest signal] Error: {e}")


@receiver(post_save, sender=PremiumRequest)
def update_premium_user_on_approval(sender, instance, **kwargs):
    """Premium so'rov tasdiqlanganda PremiumUser yangilash"""
    if instance.status == 'approved':
        try:
            # PremiumUser ni olish
            premium_user, created = PremiumUser.objects.get_or_create(user=instance.user)
            
            # PremiumUser ni yangilash
            premium_user.is_premium = True
            premium_user.status = 'active'
            premium_user.admin_approved = True
            premium_user.premium_start = timezone.now()
            premium_user.premium_end = timezone.now() + timedelta(days=instance.requested_days)
            premium_user.premium_days = instance.requested_days
            premium_user.premium_limit = instance.requested_limit
            premium_user.save()
            
            # SellerProfile ni premium qilish
            try:
                seller_profile = SellerProfile.objects.get(user=instance.user)
                seller_profile.is_premium_seller = True
                seller_profile.premium_seller_since = timezone.now()
                seller_profile.save()
            except SellerProfile.DoesNotExist:
                pass
            
            print(f"[PremiumRequest signal] PremiumUser yangilandi: {instance.user.username}")
            
        except Exception as e:
            print(f"[PremiumRequest signal] Error updating PremiumUser: {e}")


@receiver(pre_save, sender=Mahsulot)
def check_mahsulot_premium_expiry(sender, instance, **kwargs):
    """Mahsulot saqlanganda premium muddatini tekshirish"""
    # Agar premium mahsulot bo'lsa va premium muddati o'tgan bo'lsa
    if instance.is_premium and instance.premium_expiry and instance.premium_expiry < timezone.now():
        print(f"[Signal] Mahsulot premium muddati tugagan: {instance.name}")
        
        # Mahsulotni deaktivlashtirish
        instance.is_premium = False
        instance.premium_since = None
        instance.premium_expiry = None
        instance.premium_admin_approved = False
        instance.premium_priority = 0
        
        # Foydalanuvchining premium_used counterini kamaytirish
        try:
            premium_profile = PremiumUser.objects.get(user=instance.user)
            actual_count = Mahsulot.objects.filter(
                user=instance.user,
                is_premium=True,
                premium_expiry__gt=timezone.now()
            ).exclude(id=instance.id).count()
            premium_profile.premium_used = actual_count
            premium_profile.save(update_fields=['premium_used'])
        except PremiumUser.DoesNotExist:
            pass


@receiver(pre_save, sender=PremiumUser)
def check_premium_user_expiry(sender, instance, **kwargs):
    """PremiumUser saqlanganda premium muddatini tekshirish"""
    # Agar premium bo'lsa va muddati tugagan bo'lsa
    if instance.is_premium and instance.premium_end and instance.premium_end < timezone.now():
        print(f"[Signal] PremiumUser muddati tugagan: {instance.user.username}")
        
        # PremiumUser statusini yangilash
        instance.is_premium = False
        instance.status = 'expired'
        instance.premium_used = 0
        instance.notified_before_expiry = False
        instance.last_check = timezone.now()
        
        # Mahsulotlarini deaktivlashtirish
        premium_products = Mahsulot.objects.filter(
            user=instance.user,
            is_premium=True
        )
        
        for product in premium_products:
            product.is_premium = False
            product.premium_since = None
            product.premium_expiry = None
            product.premium_admin_approved = False
            product.premium_priority = 0
            product.save()
        
        # Seller profilini ham yangilash
        try:
            seller_profile = SellerProfile.objects.get(user=instance.user)
            seller_profile.is_premium_seller = False
            seller_profile.save()
        except SellerProfile.DoesNotExist:
            pass


@receiver(pre_save, sender=PremiumProduct)
def check_premium_product_expiry(sender, instance, **kwargs):
    """PremiumProduct saqlanganda premium muddatini tekshirish"""
    if instance.premium_until and instance.premium_until < timezone.now():
        print(f"[Signal] PremiumProduct muddati tugagan: {instance.mahsulot.name}")
        
        instance.is_active = False
        
        # Mahsulotni deaktivlashtirish
        if instance.mahsulot:
            instance.mahsulot.is_premium = False
            instance.mahsulot.premium_since = None
            instance.mahsulot.premium_expiry = None
            instance.mahsulot.premium_admin_approved = False
            instance.mahsulot.premium_priority = 0
            instance.mahsulot.save()


@receiver(pre_delete, sender=Mahsulot)
def decrease_premium_counter_on_delete(sender, instance, **kwargs):
    """Mahsulot o'chirilganda premium counter ni kamaytirish"""
    if instance.is_premium:
        try:
            premium_profile = PremiumUser.objects.get(user=instance.user)
            actual_count = Mahsulot.objects.filter(
                user=instance.user,
                is_premium=True,
                premium_expiry__gt=timezone.now()
            ).exclude(id=instance.id).count()
            premium_profile.premium_used = actual_count
            premium_profile.save(update_fields=['premium_used'])
        except PremiumUser.DoesNotExist:
            pass