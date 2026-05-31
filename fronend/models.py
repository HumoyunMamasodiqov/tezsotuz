from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
import json
import re
from django.core.validators import MaxValueValidator, MinValueValidator
from django.urls import reverse
from datetime import timedelta
from django.db.models import Q
from decimal import Decimal


class Banner(models.Model):
    DEVICE_CHOICES = [
        ('desktop', 'Desktop/Notebook'),
        ('mobile', 'Mobile/Tablet'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Banner nomi")
    image = models.ImageField(upload_to='banners/', verbose_name="Banner rasmi")
    device_type = models.CharField(max_length=10, choices=DEVICE_CHOICES, verbose_name="Qurilma turi")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    link = models.URLField(blank=True, null=True, verbose_name="Havola (ixtiyoriy)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")
    
    class Meta:
        verbose_name = "Banner"
        verbose_name_plural = "Bannerlar"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_device_type_display()})"


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kategoriya nomi")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    has_premium = models.BooleanField(default=False, verbose_name="Premium kategoriyami")
    premium_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Premium to'lov"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['name']
    
    def __str__(self):
        return self.name

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
import re


class SearchLog(models.Model):
    """Qidiruv loglari"""

    query = models.CharField(max_length=255)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    results_count = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['query', '-created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.query


class Mahsulot(models.Model):

    CATEGORY_CHOICES = [
        ('elektronika', 'Elektronika'),
        ('kitob', 'Kitoblar'),
        ('mebel', 'Mebellar'),
        ('cheteltovarlar', 'Chet el tovarlari'),
        ('uyjoyelonlari', 'Uy joy elonlari'),
        ('onavabollar', 'Onalar va bolalar'),
        ('avto_elonlari', 'Auto elonlar'),
        ('uy_jihozlari', 'Uy jihozlari'),
        ('kiyim', 'Kiyim-kechak'),
        ('avto', 'Avto ehtiyot qismlar'),
        ('boshqa', 'Boshqa'),
    ]

    VILOYAT_CHOICES = [
        ('toshkent', 'Toshkent'),
        ('samarqand', 'Samarqand'),
        ('fargona', 'Farg‘ona'),
        ('andijon', 'Andijon'),
        ('namangan', 'Namangan'),
        ('buxoro', 'Buxoro'),
        ('navoiy', 'Navoiy'),
        ('xorazm', 'Xorazm'),
        ('qashqadaryo', 'Qashqadaryo'),
        ('surxondaryo', 'Surxondaryo'),
        ('jizzax', 'Jizzax'),
        ('sirdaryo', 'Sirdaryo'),
        ('qoraqalpogiston', 'Qoraqalpog‘iston'),
    ]

    # ASOSIY MA'LUMOTLAR
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Foydalanuvchi"
    )

    category = models.CharField(
        max_length=100,
        choices=CATEGORY_CHOICES,
        verbose_name="Kategoriya"
    )

    mahsulotturi = models.CharField(
        max_length=100,
        verbose_name="Mahsulot turi"
    )

    name = models.CharField(
        max_length=100,
        verbose_name="Mahsulot nomi"
    )

    viloyat = models.CharField(
        max_length=100,
        choices=VILOYAT_CHOICES,
        verbose_name="Viloyat"
    )

    tuman = models.CharField(
        max_length=100,
        verbose_name="Tuman/Shahar",
        blank=True,
        null=True
    )

    manzil = models.TextField(
        verbose_name="Aniq manzil",
        blank=True,
        null=True
    )

    telefon = models.CharField(
        max_length=20,
        verbose_name="Telefon raqam",
        blank=True,
        null=True
    )

    telegram_username = models.CharField(
        max_length=100,
        verbose_name="Telegram username",
        blank=True,
        null=True
    )

    email = models.EmailField(
        verbose_name="Email",
        blank=True,
        null=True
    )

    tavsif = models.TextField(
        verbose_name="Batafsil tavsif",
        blank=True,
        null=True
    )

    sana = models.DateField(
        default=timezone.now,
        verbose_name="Sana"
    )

    narx = models.CharField(
        max_length=20,
        verbose_name="Narx",
        default="0"
    )

    # RASMLAR
    asosiyimg = models.ImageField(
        upload_to='asosiyimg/',
        verbose_name="Asosiy rasm"
    )

    birimg = models.ImageField(
        upload_to='birimg/',
        verbose_name="1-rasm",
        blank=True,
        null=True
    )

    ikkiimg = models.ImageField(
        upload_to='ikkiimg/',
        verbose_name="2-rasm",
        blank=True,
        null=True
    )

    uchuimg = models.ImageField(
        upload_to='uchuimg/',
        verbose_name="3-rasm",
        blank=True,
        null=True
    )

    toltirish = models.FileField(
        upload_to='toltirish/',
        verbose_name="Qo'shimcha fayl",
        blank=True,
        null=True
    )

    # STATUS
    sotilgan = models.BooleanField(
        default=False,
        verbose_name="Sotildi"
    )

    aktiv = models.BooleanField(
        default=True,
        verbose_name="Aktiv"
    )

    korishlar_soni = models.PositiveIntegerField(
        default=0,
        verbose_name="Ko'rishlar soni"
    )

    # SEARCH SYSTEM
    search_keywords = models.TextField(
        blank=True,
        help_text="Qidiruv kalit so'zlari"
    )

    popularity_score = models.FloatField(default=0.0)

    search_count = models.IntegerField(default=0)

    # PREMIUM
    is_premium = models.BooleanField(
        default=False,
        verbose_name="Premium mahsulotmi"
    )

    premium_since = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Premium boshlangan sana"
    )

    premium_expiry = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Premium tugash sanasi"
    )

    premium_admin_approved = models.BooleanField(
        default=False,
        verbose_name="Premium admin tasdiqladi"
    )

    premium_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Premium kunlari"
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name="Featured mahsulot"
    )

    featured_until = models.DateTimeField(
        null=True,
        blank=True
    )

    premium_priority = models.PositiveIntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10)
        ]
    )

    premium_views = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"

        ordering = [
            '-premium_priority',
            '-premium_since',
            '-sana'
        ]

        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['aktiv']),
            models.Index(fields=['sotilgan']),

            models.Index(fields=[
                'is_premium',
                'aktiv',
                'sotilgan'
            ]),

            models.Index(fields=[
                'premium_since',
                'premium_expiry'
            ]),

            models.Index(fields=[
                '-popularity_score',
                '-sana'
            ]),

            models.Index(fields=['user']),
        ]

    def __str__(self):
        premium_tag = " [PREMIUM]" if self.is_premium else ""
        return f"{self.name}{premium_tag} - {self.user.username}"

    def save(self, *args, **kwargs):
        # Premium muddati tugaganini tekshirish
        if (
            self.is_premium and
            self.premium_expiry and
            self.premium_expiry < timezone.now()
        ):
            self.is_premium = False
            self.premium_since = None
            self.premium_expiry = None
            self.premium_admin_approved = False
            self.premium_priority = 0

        super().save(*args, **kwargs)

    def get_absolute_url(self):

        from django.urls import reverse

        if self.is_premium:
            return reverse(
                'premium_product_detail',
                kwargs={'mahsulot_id': self.id}
            )

        return reverse(
            'mahsulot_detail',
            kwargs={'mahsulot_id': self.id}
        )

    def narx_formatted(self):

        try:

            if not self.narx:
                return "0 so'm"

            narx_str = str(self.narx)
            narx_str = narx_str.replace(',', '.')
            narx_str = narx_str.strip()

            narx_str = re.sub(r'[^\d.]', '', narx_str)

            if narx_str:

                narx_float = float(narx_str)

                if narx_float.is_integer():
                    return f"{int(narx_float):,} so'm".replace(',', ' ')

                return f"{narx_float:,.2f} so'm"

            return "0 so'm"

        except:
            return "0 so'm"

    def user_info(self):

        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"

        return self.user.username

    def telefon_formatted(self):

        if not self.telefon:
            return "Ko'rsatilmagan"

        numbers = re.sub(r'\D', '', self.telefon)

        if len(numbers) == 9:
            return f"+998 {numbers[:2]} {numbers[2:5]} {numbers[5:7]} {numbers[7:]}"

        elif len(numbers) == 12 and numbers.startswith('998'):
            return f"+{numbers[:3]} {numbers[3:5]} {numbers[5:8]} {numbers[8:10]} {numbers[10:]}"

        return self.telefon

    def toliq_manzil(self):

        manzil_qismlari = []

        if self.viloyat:
            manzil_qismlari.append(
                self.get_viloyat_display()
            )

        if self.tuman:
            manzil_qismlari.append(self.tuman)

        if self.manzil:
            manzil_qismlari.append(self.manzil)

        if manzil_qismlari:
            return ", ".join(manzil_qismlari)

        return "Manzil ko'rsatilmagan"

    def telegram_link(self):

        if self.telegram_username:
            username = self.telegram_username.lstrip('@')
            return f"https://t.me/{username}"

        return "#"

    def telefon_link(self):

        if not self.telefon:
            return "#"

        numbers = re.sub(r'\D', '', self.telefon)

        if len(numbers) >= 9:
            return f"tel:+998{numbers[-9:]}"

        return f"tel:{numbers}"

    def sotilgan_ha_yoq(self):

        if self.sotilgan:
            return "✅ Sotilgan"

        return "🆕 Yangi"

    # =========================
    # PREMIUM METHODS
    # =========================

    def is_premium_active(self):

        if not self.is_premium:
            return False

        if (
            self.premium_expiry and
            self.premium_expiry < timezone.now()
        ):

            self.remove_premium()
            return False

        return True

    def get_premium_time_left(self):

        if not self.is_premium:
            return "0 kun"

        if not self.premium_expiry:
            return "0 kun"

        time_left = self.premium_expiry - timezone.now()

        if time_left.days < 0:
            return "0 kun"

        return f"{time_left.days} kun"

    def get_premium_status_display(self):

        if not self.is_premium:
            return "⚫ Oddiy"

        if not self.is_premium_active():
            return "🔴 Tugagan"

        days_left = (
            self.premium_expiry - timezone.now()
        ).days

        if days_left <= 3:
            return f"🟡 {days_left} kun qoldi"

        return "🟢 Premium"

    def get_premium_badge(self):

        if self.is_premium:
            return """
            <span class="premium-badge">
                👑 PREMIUM
            </span>
            """

        return ""

    def make_premium(
        self,
        days=30,
        auto_approve=False
    ):

        if self.is_premium:
            return False, "Allaqachon premium"

        now = timezone.now()

        self.is_premium = True
        self.premium_since = now
        self.premium_expiry = now + timedelta(days=days)
        self.premium_admin_approved = auto_approve
        self.premium_days = days
        self.premium_priority = 5

        self.save()

        return True, "Premium qilindi"

    def remove_premium(self):

        self.is_premium = False
        self.premium_since = None
        self.premium_expiry = None
        self.premium_admin_approved = False
        self.premium_priority = 0

        self.save()

    def auto_renew_premium(self, days=30):

        if not self.is_premium:
            return False, "Premium emas"

        if not self.premium_expiry:
            return False, "Premium sana topilmadi"

        self.premium_expiry += timedelta(days=days)
        self.premium_days += days

        self.save()

        return True, f"{days} kunga uzaytirildi"
    

    
class Sevimli(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Foydalanuvchi")
    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.CASCADE, verbose_name="Mahsulot")
    sana = models.DateTimeField(auto_now_add=True, verbose_name="Saqlangan sana")

    class Meta:
        verbose_name = "Sevimli"
        verbose_name_plural = "Sevimlilar"
        unique_together = ['user', 'mahsulot']

    def __str__(self):
        return f"{self.user.username} - {self.mahsulot.name}"


class SellerProfile(models.Model):
    """Sotuvchi profili modeli"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='seller_profile',
        verbose_name="Foydalanuvchi"
    )
    bio = models.TextField(blank=True, null=True, verbose_name="Bio (Qisqacha ma'lumot)")
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name="Manzil")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon raqam")
    instagram = models.CharField(max_length=100, blank=True, null=True, verbose_name="Instagram username")
    telegram = models.CharField(max_length=100, blank=True, null=True, verbose_name="Telegram username")
    work_hours_start = models.TimeField(default='09:00', verbose_name="Ish vaqti boshlanishi")
    work_hours_end = models.TimeField(default='21:00', verbose_name="Ish vaqti tugashi")
    profile_image = models.ImageField(upload_to='seller_profile_images/', blank=True, null=True, verbose_name="Profil rasmi")
    banner_image = models.ImageField(upload_to='seller_banners/', blank=True, null=True, verbose_name="Banner rasm")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Premium sotuvchi maydonlari
    is_premium_seller = models.BooleanField(default=False, verbose_name="Premium sotuvchimi")
    premium_seller_since = models.DateTimeField(null=True, blank=True, verbose_name="Premium sotuvchi boshlanishi")
    seller_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Sotuvchi reytingi"
    )
    total_sales = models.PositiveIntegerField(default=0, verbose_name="Jami sotuvlar")
    
    class Meta:
        verbose_name = "Sotuvchi Profili"
        verbose_name_plural = "Sotuvchi Profillari"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Sotuvchi profili"
    
    def get_work_hours(self):
        """Ish vaqtini formatlash"""
        return f"{self.work_hours_start.strftime('%H:%M')} - {self.work_hours_end.strftime('%H:%M')}"
    
    def get_instagram_url(self):
        """Instagram URL yaratish"""
        if self.instagram:
            username = self.instagram.lstrip('@')
            return f"https://instagram.com/{username}"
        return "#"
    
    def get_telegram_url(self):
        """Telegram URL yaratish"""
        if self.telegram:
            username = self.telegram.lstrip('@')
            return f"https://t.me/{username}"
        return "#"
    
    def get_full_name(self):
        """Foydalanuvchining to'liq ismini olish"""
        if self.user.first_name or self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}".strip()
        return self.user.username


class PremiumUser(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('approved', 'Tasdiqlangan'),
        ('rejected', 'Rad etilgan'),
        ('expired', 'Muddati tugagan'),
        ('active', 'Faol'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='premium_profile',
        verbose_name="Foydalanuvchi"
    )
    is_premium = models.BooleanField(default=False, verbose_name="Premium status")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holati")
    
    # Premium vaqt maydonlari
    premium_start = models.DateTimeField(null=True, blank=True, verbose_name="Premium boshlanish vaqti")
    premium_end = models.DateTimeField(null=True, blank=True, verbose_name="Premium tugash vaqti")
    premium_days = models.PositiveIntegerField(default=30, verbose_name="Premium kunlari")
    
    admin_approved = models.BooleanField(default=False, verbose_name="Admin tasdiqlaganmi")
    premium_limit = models.PositiveIntegerField(default=5, verbose_name="Premium mahsulot limiti")
    premium_used = models.PositiveIntegerField(default=0, verbose_name="Foydalanilgan premium mahsulotlar")
    admin_notes = models.TextField(blank=True, null=True, verbose_name="Admin izohlari")
    
    # Premium so'rov
    request_premium_access = models.BooleanField(default=False, verbose_name="Premium so'rovi")
    request_date = models.DateTimeField(null=True, blank=True, verbose_name="So'rov sanasi")
    
    # Ogohlantirishlar
    notified_before_expiry = models.BooleanField(default=False, verbose_name="Premium tugashidan ogohlantirildi")
    last_check = models.DateTimeField(null=True, blank=True, verbose_name="Oxirgi tekshirilgan vaqt")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Premium Foydalanuvchi"
        verbose_name_plural = "Premium Foydalanuvchilar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['premium_end', 'is_premium', 'status']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        premium_status = "Premium" if self.is_premium else "Oddiy"
        return f"{self.user.username} - {premium_status} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Premium foydalanuvchini saqlashda avtomatik tekshirish"""
        super().save(*args, **kwargs)
        
        # Premium muddati tugaganmi tekshirish
        if self.is_premium and self.premium_end and self.premium_end < timezone.now():
            self.deactivate_premium()
    
    def deactivate_premium(self):
        """Premiumni deaktivlashtirish"""
        if not self.is_premium:
            return False
        
        try:
            # Foydalanuvchining barcha premium mahsulotlarini olish
            premium_products = Mahsulot.objects.filter(
                user=self.user,
                is_premium=True
            )
            
            # Premium mahsulotlarni deaktivlashtirish
            for product in premium_products:
                product.is_premium = False
                product.premium_since = None
                product.premium_expiry = None
                product.premium_admin_approved = False
                product.premium_priority = 0
                product.save()
            
            # PremiumUser statusini yangilash
            self.is_premium = False
            self.status = 'expired'
            self.premium_used = 0
            self.notified_before_expiry = False
            self.last_check = timezone.now()
            
            # Saqlash
            super().save()
            
            # Seller profili yangilash
            try:
                seller_profile = SellerProfile.objects.get(user=self.user)
                seller_profile.is_premium_seller = False
                seller_profile.save()
            except SellerProfile.DoesNotExist:
                pass
            return True
            
        except Exception as e:
            return False
    
    def check_and_deactivate_expired(self):
        """Premium muddati tugaganmi tekshirish va deaktivlashtirish"""
        if self.is_premium and self.premium_end and self.premium_end < timezone.now():
            return self.deactivate_premium()
        return False
    
    def can_add_premium(self):
        """Premium mahsulot qo'shish huquqini tekshirish"""
        settings = AdminPremiumSettings.get_settings()
        
        # Premium tizim yoqilganmi?
        if not settings.is_premium_enabled:
            return False, "Premium tizim hozirda faol emas"
        
        # Asosiy tekshirishlar
        if not self.is_premium:
            return False, "Siz premium foydalanuvchi emassiz"
        
        if not self.admin_approved:
            return False, "Admin tomonidan tasdiqlanmagan"
        
        if self.status not in ['approved', 'active']:
            return False, f"Premium holati: {self.get_status_display()}"
        
        # Premium muddati tugaganmi?
        if self.premium_end and timezone.now() > self.premium_end:
            self.deactivate_premium()
            return False, "Premium muddati tugagan"
        
        return True, "Premium huquqi mavjud"
    
    def can_add_more_premium_products(self):
        """Yana premium mahsulot qo'shish mumkinmi?"""
        # Avval umumiy premium huquqni tekshirish
        can_add, reason = self.can_add_premium()
        if not can_add:
            return False, reason
        
        # Limit tekshirish
        if self.premium_used >= self.premium_limit:
            return False, f"Limit tugagan (Max: {self.premium_limit}, Foydalanilgan: {self.premium_used})"
        
        return True, f"Qolgan mahsulotlar: {self.get_remaining_premium_products()}"
    
    def get_remaining_premium_products(self):
        """Qolgan premium mahsulotlar soni"""
        return max(0, self.premium_limit - self.premium_used)
    
    def get_days_remaining(self):
        """Qolgan kunlar soni"""
        if self.premium_end:
            days = (self.premium_end - timezone.now()).days
            return max(0, days)
        return 0
    
    def should_notify_expiry(self):
        """Ogohlantirish kerakmi?"""
        if not self.premium_end or not self.is_premium:
            return False
        
        settings = AdminPremiumSettings.get_settings()
        days_left = self.get_days_remaining()
        
        return days_left <= settings.notify_before_days and not self.notified_before_expiry
    
    def notify_expiry(self):
        """Ogohlantirish yuborish"""
        self.notified_before_expiry = True
        self.save(update_fields=['notified_before_expiry'])
    
    def request_premium(self):
        """Premium huquq so'rash"""
        self.request_premium_access = True
        self.request_date = timezone.now()
        self.save()
    
    def activate_premium(self, days=None, admin_user=None):
        """Premiumni faollashtirish (yangi yoki qayta)"""
        settings = AdminPremiumSettings.get_settings()
        
        # Kunlarni aniqlash
        premium_days = days or settings.premium_duration_days
        
        # Premium vaqtini belgilash
        now = timezone.now()
        self.is_premium = True
        self.admin_approved = True
        self.status = 'active'
        self.premium_start = now
        self.premium_end = now + timedelta(days=premium_days)
        self.premium_days = premium_days
        self.request_premium_access = False
        self.notified_before_expiry = False
        self.premium_used = 0
        
        if admin_user:
            self.admin_notes = f"Aktivlashtirgan admin: {admin_user.username} - {now.strftime('%Y-%m-%d %H:%M')}"
        
        # Saqlash
        super().save()
        
        # Sotuvchi profilini ham premium qilish
        try:
            seller_profile = SellerProfile.objects.get(user=self.user)
            seller_profile.is_premium_seller = True
            seller_profile.premium_seller_since = now
            seller_profile.save()
        except SellerProfile.DoesNotExist:
            pass
        return True
    
    def reject_premium(self, reason=""):
        """Premiumni rad etish"""
        self.is_premium = False
        self.admin_approved = False
        self.status = 'rejected'
        self.request_premium_access = False
        self.admin_notes = f"Rad etildi: {reason}\nSana: {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        self.save()
    
    def reset_premium_counter(self):
        """Premium counter ni yangilash"""
        # Haqiqiy premium mahsulotlar sonini hisoblash
        actual_count = Mahsulot.objects.filter(
            user=self.user,
            is_premium=True,
            premium_expiry__gt=timezone.now()
        ).count()
        
        self.premium_used = actual_count
        self.save(update_fields=['premium_used'])
        return self.premium_used
    
    def auto_renew_premium(self):
        """Premiumni avtomatik uzaytirish"""
        settings = AdminPremiumSettings.get_settings()
        
        if not settings.auto_renew_premium:
            return False, "Auto renew yoqilmagan"
        
        now = timezone.now()
        self.premium_end = now + timedelta(days=settings.auto_renew_days)
        self.premium_days += settings.auto_renew_days
        self.save()
        return True, f"Premium {settings.auto_renew_days} kunga uzaytirildi"





# models.py - PremiumRequest modeli

class PremiumRequest(models.Model):
    """Premium huquq so'rovlari"""
    
    REQUEST_STATUS = [
        ('pending', 'Kutilmoqda'),
        ('approved', 'Tasdiqlangan'),
        ('rejected', 'Rad etilgan'),
        ('expired', 'Muddati tugagan'),
        ('cancelled', 'Bekor qilingan'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Kutilmoqda'),
        ('processing', 'Qayta ishlanmoqda'),
        ('completed', 'Toʻlangan'),
        ('failed', 'Muvaffaqiyatsiz'),
        ('refunded', 'Qaytarilgan'),
    ]
    
    PAYMENT_METHODS = [
        ('bank_card', 'Bank karta'),
        ('click', 'Click'),
        ('payme', 'Payme'),
        ('uzumbank', 'Uzumbank'),
        ('cash', 'Naqd pul'),
        ('other', 'Boshqa'),
    ]
    
    # ========== Foydalanuvchi ma'lumotlari ==========
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        verbose_name="Foydalanuvchi", 
        related_name='premium_requests'
    )
    
    full_name = models.CharField(
        max_length=255, 
        verbose_name="To'liq ism", 
        help_text="Ism va familiyangizni kiriting"
    )
    
    phone = models.CharField(
        max_length=20, 
        verbose_name="Telefon raqam",
        help_text="998XXXXXXXXX formatida kiriting"
    )
    
    telegram_username = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Telegram username",
        help_text="@ belgisiz kiriting"
    )
    
    email = models.EmailField(
        blank=True, 
        null=True, 
        verbose_name="Email",
        help_text="Iltimos, haqiqiy email kiriting"
    )
    
    # ========== Premium sozlamalari ==========
    requested_days = models.PositiveIntegerField(
        default=30, 
        verbose_name="So'ralgan kunlar",
        help_text="Premium obuna davomiyligi (kunlarda)",
        validators=[MinValueValidator(1), MaxValueValidator(365)]
    )
    
    requested_limit = models.PositiveIntegerField(
        default=5, 
        verbose_name="So'ralgan limit",
        help_text="Premium mahsulotlar soni",
        validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    
    # ========== To'lov ma'lumotlari ==========
    calculated_total = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Hisoblangan summa",
        help_text="Tizim tomonidan hisoblangan summa"
    )
    
    payment_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00,
        verbose_name="To'lov summasi",
        help_text="Foydalanuvchi to'lagan summa"
    )
    
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS, 
        default='pending',
        verbose_name="To'lov holati"
    )
    
    payment_method = models.CharField(
        max_length=50, 
        choices=PAYMENT_METHODS,
        blank=True, 
        null=True, 
        verbose_name="To'lov usuli"
    )
    
    transaction_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Tranzaksiya ID",
        help_text="Bank tranzaksiya raqami yoki chek nomeri"
    )
    
    payment_date = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="To'lov sanasi"
    )
    
    payment_proof = models.FileField(
        upload_to='payment_proofs/',
        blank=True,
        null=True,
        verbose_name="To'lov dalili",
        help_text="To'lov cheki yoki skrinshoti"
    )
    
    # ========== Status va ma'lumotlar ==========
    status = models.CharField(
        max_length=20, 
        choices=REQUEST_STATUS, 
        default='pending', 
        verbose_name="Holati"
    )
    
    notes = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Qo'shimcha eslatmalar",
        help_text="Foydalanuvchi qo'shimcha ma'lumotlari"
    )
    
    admin_notes = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Admin izohlari",
        help_text="Admin qo'shimcha izohlari"
    )
    
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Rad etish sababi",
        help_text="Agar so'rov rad etilsa, sababi"
    )
    
    # ========== Admin va vaqt ==========
    admin_user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_requests', 
        verbose_name="Tasdiqlagan admin"
    )
    
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_requests',
        verbose_name="Qayta ishlagan admin"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Yaratilgan sana"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="Yangilangan sana"
    )
    
    approved_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Tasdiqlangan sana"
    )
    
    expired_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Muddati tugagan sana"
    )
    
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Bekor qilingan sana"
    )
    
    # ========== Qo'shimcha maydonlar ==========
    auto_approve = models.BooleanField(
        default=False,
        verbose_name="Avtomatik tasdiqlansinmi",
        help_text="To'lov tasdiqlangandan so'ng avtomatik tasdiqlansinmi?"
    )
    
    notification_sent = models.BooleanField(
        default=False,
        verbose_name="Bildirishnoma yuborilganmi"
    )
    
    viewed_by_admin = models.BooleanField(
        default=False,
        verbose_name="Admin ko'rganmi"
    )
    
    priority = models.PositiveIntegerField(
        default=0,
        verbose_name="Prioritet",
        help_text="Yuqoriroq prioritet birinchi ko'rsatiladi"
    )
    
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="IP manzil"
    )
    
    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name="User Agent"
    )
    
    class Meta:
        verbose_name = "Premium So'rovi"
        verbose_name_plural = "Premium So'rovlari"
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['phone']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['approved_at']),
        ]
        permissions = [
            ("can_approve_requests", "Premium so'rovlarni tasdiqlash huquqi"),
            ("can_reject_requests", "Premium so'rovlarni rad etish huquqi"),
            ("can_view_payment_proof", "To'lov dalillarini ko'rish huquqi"),
            ("can_export_requests", "So'rovlarni export qilish huquqi"),
        ]
    
    def __str__(self):
        return f"#{self.id} - {self.full_name} ({self.get_status_display()})"
    
    def clean(self):
        """Forma validatsiyasi"""
        from django.core.exceptions import ValidationError
        
        # Telefon raqam validatsiyasi
        if self.phone:
            cleaned_phone = re.sub(r'\D', '', self.phone)
            if len(cleaned_phone) != 9 and len(cleaned_phone) != 12:
                raise ValidationError({
                    'phone': "Telefon raqami noto'g'ri formatda. 998XXXXXXXXX yoki 9XXXXXXXX formatida kiriting."
                })
        
        # Email validatsiyasi
        if self.email:
            # Oddiy email validatsiyasi
            if '@' not in self.email or '.' not in self.email:
                raise ValidationError({'email': "Email manzili noto'g'ri formatda."})
        
        # Kunlar validatsiyasi
        if self.requested_days < 1 or self.requested_days > 365:
            raise ValidationError({
                'requested_days': "Premium kunlari 1 dan 365 gacha bo'lishi kerak."
            })
        
        # Limit validatsiyasi
        if self.requested_limit < 1 or self.requested_limit > 50:
            raise ValidationError({
                'requested_limit': "Mahsulot limiti 1 dan 50 gacha bo'lishi kerak."
            })
        
        # Foydalanuvchining aktiv Premium borligini tekshirish
        if not self.id:  # Faqat yangi yaratilayotganda
            try:
                premium_profile = PremiumUser.objects.get(user=self.user)
                
                if premium_profile.is_premium and premium_profile.status == 'active':
                    if premium_profile.premium_end and premium_profile.premium_end > timezone.now():
                        qolgan_kunlar = (premium_profile.premium_end - timezone.now()).days
                        premium_tugash = premium_profile.premium_end.strftime('%d.%m.%Y')
                        
                        raise ValidationError(
                            f"Sizda aktiv Premium obuna mavjud! Premium {qolgan_kunlar} kundan keyin "
                            f"({premium_tugash}) tugaydi. Premium tugagach yangi so'rov yuborishingiz mumkin."
                        )
            except PremiumUser.DoesNotExist:
                pass
        
        super().clean()
    
    def save(self, *args, **kwargs):
        """Model saqlash"""
        # Telefonni tozalash
        if self.phone:
            self.phone = re.sub(r'\D', '', self.phone)
            if len(self.phone) == 9:
                self.phone = f"998{self.phone}"
        
        # Telegram username ni tozalash
        if self.telegram_username:
            self.telegram_username = self.telegram_username.lstrip('@')
        
        # Hisoblangan summani aniqlash
        if not self.calculated_total or self.calculated_total == 0:
            settings = AdminPremiumSettings.get_settings()
            self.calculated_total = settings.calculate_price(
                self.requested_days, 
                self.requested_limit
            )
        
        # Agar to'lov summasi kiritilmagan bo'lsa, hisoblangan summani o'rnatish
        if not self.payment_amount or self.payment_amount == 0:
            self.payment_amount = self.calculated_total
        
        # Validatsiyani o'tkazish
        self.clean()
        
        # Status o'zgarishlarini kuzatish
        old_status = None
        if self.id:
            try:
                old_instance = PremiumRequest.objects.get(id=self.id)
                old_status = old_instance.status
            except PremiumRequest.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Status o'zgarganda bildirishnoma yuborish
        if old_status != self.status:
            self.send_status_notification()
    
    def get_days_since_request(self):
        """So'rov berilganidan buyon o'tgan kunlar"""
        return (timezone.now() - self.created_at).days
    
    def get_hours_since_request(self):
        """So'rov berilganidan buyon o'tgan soatlar"""
        return int((timezone.now() - self.created_at).total_seconds() / 3600)
    
    def is_expired(self):
        """So'rov muddati o'tganmi?"""
        if self.status in ['approved', 'rejected', 'expired', 'cancelled']:
            return False
        
        settings = AdminPremiumSettings.get_settings()
        days_since = self.get_days_since_request()
        
        if days_since > settings.premium_request_expiry_days:
            return True
        
        return False
    
    def mark_as_expired(self):
        """So'rovni muddati o'tgan qilish"""
        if self.status == 'pending':
            self.status = 'expired'
            self.expired_at = timezone.now()
            self.save()
            return True
        return False
    
    def cancel_request(self):
        """So'rovni bekor qilish"""
        if self.status == 'pending':
            self.status = 'cancelled'
            self.cancelled_at = timezone.now()
            self.save()
            
            # Foydalanuvchiga bildirishnoma
            self.send_notification(
                title="So'rovingiz Bekor Qilindi",
                message="Sizning premium so'rovingiz bekor qilindi.",
                notification_type='request_cancelled'
            )
            return True
        return False
    
    def get_payment_details(self):
        """To'lov ma'lumotlarini olish"""
        return {
            'amount': self.payment_amount,
            'calculated_amount': self.calculated_total,
            'difference': self.payment_amount - self.calculated_total,
            'status': self.get_payment_status_display(),
            'method': self.get_payment_method_display() if self.payment_method else "Ko'rsatilmagan",
            'date': self.payment_date.strftime('%d.%m.%Y %H:%M') if self.payment_date else None,
            'transaction_id': self.transaction_id or "Yo'q",
            'has_proof': bool(self.payment_proof),
        }
    
    def confirm_payment(self, transaction_id=None, payment_method=None, proof_file=None):
        """To'lovni tasdiqlash"""
        self.payment_status = 'completed'
        self.payment_date = timezone.now()
        
        if transaction_id:
            self.transaction_id = transaction_id
        
        if payment_method:
            self.payment_method = payment_method
            
        if proof_file:
            self.payment_proof = proof_file
        
        # Agar auto_approve yoqilgan bo'lsa
        if self.auto_approve and self.status == 'pending':
            self.approve(admin_user=None)
        
        self.save()
        
        # To'lov tasdiqlandi haqida bildirishnoma
        self.send_notification(
            title="✅ To'lov Tasdiqlandi",
            message=f"To'lovingiz muvaffaqiyatli tasdiqlandi. Tranzaksiya ID: {transaction_id}",
            notification_type='payment_confirmed'
        )
        
        return True
    
    def fail_payment(self, reason=""):
        """To'lovni muvaffaqiyatsiz qilish"""
        self.payment_status = 'failed'
        if reason:
            self.admin_notes = f"To'lov muvaffaqiyatsiz: {reason}\n{self.admin_notes or ''}"
        self.save()
        
        # To'lov muvaffaqiyatsiz haqida bildirishnoma
        self.send_notification(
            title="❌ To'lov Muvaffaqiyatsiz",
            message=f"To'lovingiz muvaffaqiyatsiz tugadi. Sabab: {reason}",
            notification_type='payment_failed'
        )
        
        return True
    
    def refund_payment(self, reason=""):
        """To'lovni qaytarish"""
        self.payment_status = 'refunded'
        if reason:
            self.admin_notes = f"To'lov qaytarildi: {reason}\n{self.admin_notes or ''}"
        self.save()
        
        return True
    
    def approve(self, admin_user=None, approved_days=None, approved_limit=None):
        """So'rovni tasdiqlash"""
        try:
            
            # Agar allaqachon tasdiqlangan bo'lsa
            if self.status == 'approved':
                return True
            
            # Kun va limitni aniqlash
            days = approved_days or self.requested_days
            limit = approved_limit or self.requested_limit
            
            now = timezone.now()
            
            # 1. PremiumUser ni yaratish yoki yangilash
            premium_user, created = PremiumUser.objects.get_or_create(
                user=self.user,
                defaults={
                    'is_premium': True,
                    'status': 'active',
                    'admin_approved': True,
                    'premium_start': now,
                    'premium_end': now + timedelta(days=days),
                    'premium_days': days,
                    'premium_limit': limit,
                    'premium_used': 0,
                    'request_premium_access': False,
                    'notified_before_expiry': False,
                    'last_check': now,
                }
            )
            
            if not created:
                # PremiumUser allaqachon mavjud, yangilash
                premium_user.is_premium = True
                premium_user.status = 'active'
                premium_user.admin_approved = True
                premium_user.premium_start = now
                premium_user.premium_end = now + timedelta(days=days)
                premium_user.premium_days = days
                premium_user.premium_limit = limit
                premium_user.request_premium_access = False
                premium_user.notified_before_expiry = False
                premium_user.last_check = now
            
            premium_user.save()
            
            # 2. SellerProfile ni yangilash
            seller_profile, _ = SellerProfile.objects.get_or_create(user=self.user)
            seller_profile.is_premium_seller = True
            seller_profile.premium_seller_since = now
            seller_profile.save()

            # 3. PremiumRequest ni yangilash
            self.status = 'approved'
            self.admin_user = admin_user
            self.approved_by = admin_user
            self.approved_at = now
            self.save()
            
            # 4. Foydalanuvchiga bildirishnoma
            try:
                PremiumNotification.objects.create(
                    user=self.user,
                    notification_type='admin_action',
                    title="Premium So'rovingiz Tasdiqlandi!",
                    message=f"""Tabriklaymiz! Sizning premium so'rovingiz tasdiqlandi.
                    
                            Premium ma'lumotlaringiz:
                            - Muddati: {days} kun
                            - Mahsulot limiti: {limit} ta
                            - Premium boshlanishi: {now.strftime('%d.%m.%Y %H:%M')}
                            - Premium tugashi: {(now + timedelta(days=days)).strftime('%d.%m.%Y %H:%M')}
                            """,
                    data={
                        'request_id': self.id,
                        'days': days,
                        'limit': limit,
                        'premium_start': now.isoformat(),
                        'premium_end': premium_user.premium_end.isoformat() if premium_user.premium_end else None
                    }
                )
            except Exception:
                pass

            # 5. Adminlarga bildirishnoma (agar admin_user mavjud bo'lsa)
            if admin_user:
                try:
                    create_admin_notification(
                        title="Premium So'rov Tasdiqlandi",
                        message=f"{admin_user.username} tomonidan {self.full_name} ning so'rovi tasdiqlandi.",
                        data={'request_id': self.id, 'admin': admin_user.username}
                    )
                except:
                    pass
            return True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False
    
    def reject(self, admin_user=None, reason=""):
        """So'rovni rad etish"""
        self.status = 'rejected'
        self.admin_user = admin_user
        self.approved_by = admin_user
        self.admin_notes = reason
        self.rejection_reason = reason
        self.save()
        
        # Foydalanuvchiga bildirishnoma
        try:
            PremiumNotification.objects.create(
                user=self.user,
                notification_type='admin_action',
                title="Premium So'rovingiz Rad Etildi",
                message=f"Sizning premium so'rovingiz rad etildi. Sabab: {reason}",
                data={'request_id': self.id, 'reason': reason}
            )
        except:
            pass
        
        return True
    
    def send_status_notification(self):
        """Status o'zgarganda bildirishnoma yuborish"""
        status_messages = {
            'pending': {
                'title': "Premium So'rovingiz Qabul Qilindi",
                'message': "Sizning premium so'rovingiz qabul qilindi va tekshirish uchun yuborildi."
            },
            'approved': {
                'title': "🎉 Premium So'rovingiz Tasdiqlandi!",
                'message': "Tabriklaymiz! Sizning premium so'rovingiz tasdiqlandi."
            },
            'rejected': {
                'title': "Premium So'rovingiz Rad Etildi",
                'message': f"Sizning premium so'rovingiz rad etildi. Sabab: {self.rejection_reason}"
            },
            'expired': {
                'title': "Premium So'rovingiz Muddati Tugadi",
                'message': "Sizning premium so'rovingiz muddati tugadi."
            },
            'cancelled': {
                'title': "Premium So'rovingiz Bekor Qilindi",
                'message': "Sizning premium so'rovingiz bekor qilindi."
            }
        }
        
        if self.status in status_messages:
            msg = status_messages[self.status]
            self.send_notification(
                title=msg['title'],
                message=msg['message'],
                notification_type='status_change'
            )
    
    def send_notification(self, title, message, notification_type='info'):
        """Bildirishnoma yuborish"""
        try:
            PremiumNotification.objects.create(
                user=self.user,
                notification_type=notification_type,
                title=title,
                message=message,
                data={
                    'request_id': self.id,
                    'request_status': self.status,
                    'notification_type': notification_type
                }
            )
            self.notification_sent = True
            self.save(update_fields=['notification_sent'])
            return True
        except Exception as e:
            return False
    
    def get_formatted_phone(self):
        """Telefon raqamini formatlash"""
        if not self.phone:
            return ""
        
        phone = str(self.phone)
        if phone.startswith('998') and len(phone) == 12:
            return f"+{phone[:3]} {phone[3:5]} {phone[5:8]} {phone[8:10]} {phone[10:]}"
        elif len(phone) == 9:
            return f"+998 {phone[:2]} {phone[2:5]} {phone[5:7]} {phone[7:]}"
        else:
            return phone
    
    def get_telegram_link(self):
        """Telegram linkini olish"""
        if self.telegram_username:
            return f"https://t.me/{self.telegram_username}"
        return None
    
    def get_payment_proof_url(self):
        """To'lov dalili URL"""
        if self.payment_proof:
            return self.payment_proof.url
        return None
    
    def get_admin_url(self):
        """Admin panel linki"""
        from django.urls import reverse
        return reverse('admin:%s_%s_change' % (self._meta.app_label, self._meta.model_name), args=[self.id])
    
    def get_user_url(self):
        """Foydalanuvchi panel linki"""
        from django.urls import reverse
        return reverse('premium_request_detail', args=[self.id])
    
    def can_be_cancelled(self):
        """Bekor qilinish mumkinmi?"""
        return self.status == 'pending'
    
    def can_be_approved(self):
        """Tasdiqlanish mumkinmi?"""
        return self.status in ['pending']
    
    def can_be_rejected(self):
        """Rad etilishi mumkinmi?"""
        return self.status in ['pending']
    
    def can_be_edited(self):
        """Tahrirlanish mumkinmi?"""
        return self.status == 'pending'
    
    def get_status_color(self):
        """Status rangini olish"""
        colors = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'expired': 'secondary',
            'cancelled': 'dark',
        }
        return colors.get(self.status, 'secondary')
    
    def get_payment_status_color(self):
        """To'lov statusi rangini olish"""
        colors = {
            'pending': 'warning',
            'processing': 'info',
            'completed': 'success',
            'failed': 'danger',
            'refunded': 'dark',
        }
        return colors.get(self.payment_status, 'secondary')
    
    def calculate_discount(self):
        """Chegirma miqdorini hisoblash"""
        settings = AdminPremiumSettings.get_settings()
        
        if settings.has_discount and settings.is_discount_active():
            discount_amount = self.calculated_total * (settings.discount_percentage / 100)
            discounted_total = self.calculated_total - discount_amount
            return {
                'has_discount': True,
                'percentage': settings.discount_percentage,
                'discount_amount': discount_amount,
                'original_total': self.calculated_total,
                'discounted_total': discounted_total
            }
        
        return {
            'has_discount': False,
            'original_total': self.calculated_total
        }







class PremiumProduct(models.Model):
    """Premium mahsulotlar modeli"""
    mahsulot = models.OneToOneField(
        Mahsulot, 
        on_delete=models.CASCADE,
        related_name='premium_info',
        verbose_name="Mahsulot"
    )
    premium_owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='premium_products',
        verbose_name="Premium egasi"
    )
    admin_approved = models.BooleanField(default=False, verbose_name="Admin tasdiqlaganmi")
    approval_date = models.DateTimeField(null=True, blank=True, verbose_name="Tasdiqlangan sana")
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_premium_products',
        verbose_name="Tasdiqlagan admin"
    )
    premium_since = models.DateTimeField(auto_now_add=True, verbose_name="Premium boshlangan sana")
    premium_until = models.DateTimeField(null=True, blank=True, verbose_name="Premium tugash sanasi")
    is_active = models.BooleanField(default=True, verbose_name="Premium aktivmi")
    notes = models.TextField(blank=True, null=True, verbose_name="Qo'shimcha eslatmalar")
    
    class Meta:
        verbose_name = "Premium Mahsulot"
        verbose_name_plural = "Premium Mahsulotlar"
        ordering = ['-premium_since']
        indexes = [
            models.Index(fields=['admin_approved', 'is_active']),
            models.Index(fields=['premium_until']),
        ]
    
    def __str__(self):
        return f"Premium: {self.mahsulot.name}"
    
    def save(self, *args, **kwargs):
        if self.premium_until and self.premium_until < timezone.now():
            self.is_active = False
            self.mahsulot.remove_premium()
        
        super().save(*args, **kwargs)
    
    def approve_premium(self, admin_user):
        self.admin_approved = True
        self.approval_date = timezone.now()
        self.approved_by = admin_user
        self.is_active = True
        self.save()
        
        self.mahsulot.is_premium = True
        self.mahsulot.premium_since = timezone.now()
        self.mahsulot.premium_admin_approved = True
        self.mahsulot.save()
    
    def mark_as_regular(self):
        self.is_active = False
        self.save()
        self.mahsulot.remove_premium()


class PremiumNotification(models.Model):
    """Premium ogohlantirishlar"""
    NOTIFICATION_TYPES = [
        ('expiry_soon', 'Premium muddati tugash arafasida'),
        ('expired', 'Premium muddati tugadi'),
        ('new_request', 'Yangi premium so\'rovi'),
        ('admin_action', 'Admin harakati'),
        ('product_limit', 'Mahsulot limiti tugab qoldi'),
        ('auto_renewed', 'Premium avtomatik uzaytirildi'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='premium_notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_notification_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class AdminAloqa(models.Model):
    """Admin aloqa modeli"""
    manzil = models.CharField(max_length=255, null=False, blank=False, verbose_name="Manzil")
    telefon = models.CharField(max_length=20, null=False, blank=False, verbose_name="Telefon raqami")
    email = models.EmailField(null=False, blank=True, verbose_name="Elektron pochta")
    telegram = models.URLField(null=False, blank=True, verbose_name="Telegram havolasi")
    instagram = models.URLField(null=False, blank=True, verbose_name="Instagram havolasi")
    facebook = models.URLField(null=False, blank=True, verbose_name="Facebook havolasi")
    
    def __str__(self):
        return f"{self.manzil} - {self.email}"


class SotibOlish(models.Model):
    STATUS_CHOICES = [
        ('yangi', 'Yangi buyurtma'),
        ('qabul_qilindi', 'Sotuvchi qabul qildi'),
        ('yuborildi', 'Jo\'natildi'),
        ('yetkazildi', 'Yetkazildi'),
        ('bajarildi', 'Bajarildi'),
        ('bekor_qilindi', 'Bekor qilindi'),
    ]

    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.CASCADE, verbose_name="Mahsulot", related_name='sotib_olishlar')
    xaridor = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Xaridor", related_name='sotib_olganlarim')
    sotuvchi = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Sotuvchi", related_name='sotilgan_mahsulotlarim')
    miqdor = models.PositiveIntegerField(default=1, verbose_name="Miqdor")
    narx = models.CharField(max_length=20, verbose_name="Narx")
    jami_narx = models.CharField(max_length=20, verbose_name="Jami narx")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='yangi', verbose_name="Holati")
    
    xaridor_ism = models.CharField(max_length=255, verbose_name="Xaridor ismi", blank=True)
    xaridor_telefon = models.CharField(max_length=20, verbose_name="Xaridor telefoni", blank=True)
    xaridor_manzil = models.TextField(verbose_name="Yetkazib berish manzili", blank=True)
    xaridor_izoh = models.TextField(verbose_name="Buyurtma izohi", blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")
    read_by_seller = models.BooleanField(default=False, verbose_name="Sotuvchi ko'rganmi")
    read_by_admin = models.BooleanField(default=False, verbose_name="Admin ko'rganmi")

    class Meta:
        verbose_name = "Sotib olish"
        verbose_name_plural = "Sotib olishlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['xaridor', 'status']),
            models.Index(fields=['sotuvchi', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"#{self.id} {self.mahsulot.name} - {self.xaridor.username}"

    def save(self, *args, **kwargs):
        if not self.narx:
            self.narx = self.mahsulot.narx
        if not self.jami_narx:
            try:
                narx_int = int(float(re.sub(r'[^\d.]', '', str(self.mahsulot.narx)) or 0))
                self.jami_narx = str(narx_int * self.miqdor)
            except (ValueError, TypeError):
                self.jami_narx = self.mahsulot.narx
        if not self.xaridor_ism:
            self.xaridor_ism = self.xaridor.get_full_name() or self.xaridor.username
        if not self.xaridor_telefon:
            try:
                self.xaridor_telefon = self.xaridor.seller_profile.phone or ''
            except AttributeError:
                pass
        super().save(*args, **kwargs)


# SIGNALLAR
@receiver(post_save, sender=PremiumRequest)
def handle_premium_request_save(sender, instance, created, **kwargs):
    if instance.status == 'approved':
        PremiumUser.objects.get_or_create(
            user=instance.user,
            defaults={
                'is_premium': True,
                'status': 'active',
                'admin_approved': True,
                'premium_start': timezone.now(),
                'premium_end': timezone.now() + timedelta(days=instance.requested_days),
                'premium_days': instance.requested_days,
                'premium_limit': instance.requested_limit,
                'premium_used': 0
            }
        )


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Yangi foydalanuvchi yaratilganda profil yaratish"""
    if created:
        SellerProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Foydalanuvchi saqlanganda profilni saqlash"""
    try:
        instance.seller_profile.save()
    except SellerProfile.DoesNotExist:
        SellerProfile.objects.create(user=instance)











class AdminPremiumSettings(models.Model):
    """Admin uchun premium sozlamalar"""
    
    # 1. Premium narx sozlamalari (ASOSIYSI)
    premium_fee_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=15000.00,
        verbose_name="1 ta mahsulot narxi",
        help_text="1 ta mahsulotni premium qilish uchun narx"
    )
    
    premium_per_day_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=2000.00,
        verbose_name="Kunlik premium narx",
        help_text="1 kunlik premium uchun narx"
    )
    
    premium_per_week_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=12000.00,
        verbose_name="1 haftalik narx",
        help_text="1 haftalik premium narx (7 kun)"
    )
    
    premium_per_month_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=60000.00,
        verbose_name="1 oylik narx",
        help_text="1 oylik premium narx (30 kun)"
    )
    
    premium_per_3months_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=150000.00,
        verbose_name="3 oylik narx",
        help_text="3 oylik premium narx (90 kun)"
    )
    
    premium_per_6months_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=270000.00,
        verbose_name="6 oylik narx",
        help_text="6 oylik premium narx (180 kun)"
    )
    
    premium_per_year_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=500000.00,
        verbose_name="1 yillik narx",
        help_text="1 yillik premium narx (365 kun)"
    )
    
    # 2. Chegirma sozlamalari
    has_discount = models.BooleanField(
        default=False,
        verbose_name="Chegirma yoqilsinmi",
        help_text="Premium uchun chegirma mavjudmi?"
    )
    
    discount_percentage = models.PositiveIntegerField(
        default=10,
        verbose_name="Chegirma foizi",
        help_text="Chegirma foizi (%)",
        validators=[MaxValueValidator(50), MinValueValidator(0)]
    )
    
    discount_end_date = models.DateField(
        null=True, blank=True,
        verbose_name="Chegirma tugash sanasi",
        help_text="Chegirma tugash sanasi (ixtiyoriy)"
    )
    
    # 3. Asosiy sozlamalar
    is_premium_enabled = models.BooleanField(
        default=True,
        verbose_name="Premium tizim yoqilganmi"
    )
    
    max_premium_products = models.PositiveIntegerField(
        default=5,
        verbose_name="Premium mahsulot limiti",
        help_text="1 premium foydalanuvchi uchun max mahsulotlar"
    )
    
    # YANGI: Premium duration days qo'shildi
    premium_duration_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Premium muddati (kun)",
        help_text="Premium obuna muddati kunlarda"
    )
    
    # YANGI: Auto approve sozlamalari
    auto_approve_premium = models.BooleanField(
        default=False,
        verbose_name="Premiumni avtomatik tasdiqlash",
        help_text="Premium mahsulotlarni avtomatik tasdiqlash"
    )
    
    # YANGI: Auto renew sozlamalari
    auto_renew_premium = models.BooleanField(
        default=False,
        verbose_name="Premiumni avtomatik uzaytirish",
        help_text="Premium muddati tugaganda avtomatik uzaytirish"
    )
    
    auto_renew_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Avtomatik uzaytirish kuni",
        help_text="Avtomatik uzaytiriladigan kunlar soni"
    )
    
    # YANGI: Admin tasdiqlash
    require_admin_approval = models.BooleanField(
        default=True,
        verbose_name="Admin tasdigini talab qilish",
        help_text="Premium so'rovlar admin tasdigini talab qilsinmi?"
    )
    
    # YANGI: Premium so'rovlar limiti
    max_premium_requests_per_user = models.PositiveIntegerField(
        default=3,
        verbose_name="Premium so'rovlar limiti",
        help_text="1 foydalanuvchi oyiga nechta so'rov yuborishi mumkin"
    )
    
    # YANGI: Premium so'rov muddati
    premium_request_expiry_days = models.PositiveIntegerField(
        default=7,
        verbose_name="Premium so'rov muddati",
        help_text="Premium so'rov qancha kunga amal qiladi"
    )
    
    # YANGI: Ogohlantirish
    notify_before_days = models.PositiveIntegerField(
        default=3,
        verbose_name="Ogohlantirish kuni",
        help_text="Premium tugashidan necha kun oldin ogohlantirish"
    )
    
    # 4. Aloqa ma'lumotlari
    admin_contact_phone = models.CharField(
        max_length=20, default="+998901234567",
        verbose_name="Admin telefon raqami"
    )
    
    admin_contact_telegram = models.CharField(
        max_length=100, default="@tezsot_admin",
        verbose_name="Admin Telegram"
    )
    
    admin_contact_email = models.EmailField(
        default="admin@tezsot.uz",
        verbose_name="Admin Email"
    )
    
    # 5. To'lov ma'lumotlari
    payment_methods = models.TextField(
        blank=True, null=True,
        default="Bank karta\nClick\nPayme\nUzumbank",
        verbose_name="To'lov usullari",
        help_text="Har bir usul yangi qatorda"
    )
    
    bank_card_number = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name="Bank karta raqami",
        help_text="To'lov qilish uchun karta raqami"
    )
    
    bank_name = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Bank nomi",
        help_text="Bank nomi"
    )
    
    bank_card_owner = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Karta egasi",
        help_text="Karta egasining ismi"
    )
    
    # 6a. Banner va Featured narxlari
    banner_price_per_day = models.DecimalField(
        max_digits=10, decimal_places=2, default=5000.00,
        verbose_name="Banner narxi (1 kun)",
        help_text="Banner reklama uchun 1 kunlik narx"
    )
    
    featured_price_per_day = models.DecimalField(
        max_digits=10, decimal_places=2, default=3000.00,
        verbose_name="Top mahsulot narxi (1 kun)",
        help_text="Top/Featured mahsulot uchun 1 kunlik narx"
    )
    
    # 6. Vaqt
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Premium Sozlamalar"
        verbose_name_plural = "Premium Sozlamalar"
        constraints = [
            models.CheckConstraint(check=models.Q(id=1), name='single_admin_premium_settings')
        ]
    
    def __str__(self):
        return f"Premium Sozlamalar"
    
    @classmethod
    def get_settings(cls):
        """Sozlamalarni olish"""
        settings, created = cls.objects.get_or_create(id=1)
        return settings
    
    def calculate_price(self, days, products):
        """Kun va mahsulotlar soniga qarab narx hisoblash"""
        from decimal import Decimal
        
        # Kunlik narx
        if days == 7:
            days_price = self.premium_per_week_price or Decimal('12000')
        elif days == 30:
            days_price = self.premium_per_month_price or Decimal('60000')
        elif days == 90:
            days_price = self.premium_per_3months_price or Decimal('150000')
        elif days == 180:
            days_price = self.premium_per_6months_price or Decimal('270000')
        elif days == 365:
            days_price = self.premium_per_year_price or Decimal('500000')
        else:
            days_price = (self.premium_per_day_price or Decimal('2000')) * days
        
        # Mahsulotlar narxi
        products_price = (self.premium_fee_amount or Decimal('15000')) * products
        
        # Jami
        total = days_price + products_price
        
        # Chegirma
        if self.has_discount and self.is_discount_active():
            discount = total * (self.discount_percentage / 100)
            total = total - discount
        
        return total
    
    def is_discount_active(self):
        """Chegirma faolmi?"""
        if not self.has_discount:
            return False
        
        if not self.discount_end_date:
            return True
        
        return timezone.now().date() <= self.discount_end_date
    
    def get_payment_methods_list(self):
        """To'lov usullari ro'yxati"""
        if self.payment_methods:
            return [m.strip() for m in self.payment_methods.split('\n') if m.strip()]
        return ["Bank karta", "Click", "Payme", "Uzumbank"]


class BannerPurchase(models.Model):
    """Foydalanuvchi tomonidan banner sotib olish"""
    STATUS_CHOICES = [
        ('kutilmoqda', "Kutilmoqda"),
        ('tasdiqlandi', "Tasdiqlangan"),
        ('aktiv', 'Aktiv'),
        ('tugadi', 'Tugagan'),
        ('bekor_qilindi', 'Bekor qilindi'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Foydalanuvchi")
    title = models.CharField(max_length=255, verbose_name="Banner sarlavhasi")
    image = models.ImageField(upload_to='banner_purchases/', verbose_name="Banner rasmi")
    link = models.URLField(blank=True, null=True, verbose_name="Havola")
    device_type = models.CharField(max_length=10, choices=Banner.DEVICE_CHOICES, default='desktop', verbose_name="Qurilma turi")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='kutilmoqda', verbose_name="Holati")
    days = models.PositiveIntegerField(default=30, verbose_name="Necha kun")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=50000.00, verbose_name="Narxi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Tasdiqlangan sana")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugash sanasi")
    payment_proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True, verbose_name="To'lov cheki")
    payment_status = models.CharField(max_length=20, default='pending', verbose_name="To'lov holati")
    
    class Meta:
        verbose_name = "Banner xaridi"
        verbose_name_plural = "Banner xaridlari"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def approve(self):
        if self.status in ['aktiv', 'tugadi', 'bekor_qilindi']:
            return
        self.status = 'aktiv'
        self.approved_at = timezone.now()
        self.expires_at = timezone.now() + timedelta(days=self.days)
        self.save()


class FeaturedPurchase(models.Model):
    """Mahsulotni featured/top qilish uchun xarid"""
    STATUS_CHOICES = [
        ('kutilmoqda', "Kutilmoqda"),
        ('tasdiqlandi', "Tasdiqlangan"),
        ('aktiv', 'Aktiv'),
        ('tugadi', 'Tugagan'),
        ('bekor_qilindi', 'Bekor qilindi'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Foydalanuvchi")
    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.CASCADE, verbose_name="Mahsulot", related_name='featured_purchases')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='kutilmoqda', verbose_name="Holati")
    days = models.PositiveIntegerField(default=7, verbose_name="Necha kun")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=20000.00, verbose_name="Narxi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Tasdiqlangan sana")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugash sanasi")
    admin_notes = models.TextField(blank=True, null=True, verbose_name="Admin izohi")
    payment_proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True, verbose_name="To'lov cheki")
    payment_status = models.CharField(max_length=20, default='pending', verbose_name="To'lov holati")
    
    class Meta:
        verbose_name = "Featured xarid"
        verbose_name_plural = "Featured xaridlari"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.mahsulot.name} - {self.user.username}"
    
    def approve(self):
        if self.status in ['aktiv', 'tugadi', 'bekor_qilindi']:
            return
        self.status = 'aktiv'
        self.approved_at = timezone.now()
        self.expires_at = timezone.now() + timedelta(days=self.days)
        self.mahsulot.is_featured = True
        self.mahsulot.featured_until = self.expires_at
        self.mahsulot.save()
        self.save()
    
    def deactivate(self):
        self.status = 'tugadi'
        self.mahsulot.is_featured = False
        self.mahsulot.featured_until = None
        self.mahsulot.save()
        self.save()


class Chat(models.Model):
    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.CASCADE, verbose_name="Mahsulot", related_name='chats')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Xaridor", related_name='chats_as_buyer')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Sotuvchi", related_name='chats_as_seller')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Chat"
        verbose_name_plural = "Chatlar"
        ordering = ['-updated_at']
        unique_together = ['mahsulot', 'buyer']

    def __str__(self):
        return f"{self.buyer.username} - {self.seller.username} | {self.mahsulot.name}"

    def last_message(self):
        return self.messages.order_by('-created_at').first()

    def unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, verbose_name="Chat", related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Yuboruvchi", related_name='sent_messages')
    text = models.TextField(verbose_name="Xabar matni")
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True, verbose_name="Rasm")
    is_read = models.BooleanField(default=False, verbose_name="O'qilganmi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuborilgan")

    class Meta:
        verbose_name = "Xabar"
        verbose_name_plural = "Xabarlar"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.text[:50]}"
