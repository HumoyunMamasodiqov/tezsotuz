# authentication/models.py
from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    birth_date = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    # Qo'shimcha maydonlar
    secondary_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Ikkinchi telefon")
    telegram = models.CharField(max_length=100, null=True, blank=True, verbose_name="Telegram username")
    instagram = models.CharField(max_length=100, null=True, blank=True, verbose_name="Instagram username")
    location = models.CharField(max_length=255, null=True, blank=True, verbose_name="Manzil")
    bio = models.TextField(null=True, blank=True, verbose_name="Bio")
    
    # Yangi maydon: foydalanuvchi shartlariga rozilik
    terms_accepted = models.BooleanField(default=False, verbose_name="Foydalanuvchi shartlariga rozimi")
    terms_accepted_at = models.DateTimeField(null=True, blank=True, verbose_name="Rozilik sanasi")
    
    # Profil rasmi (agar kerak bo'lsa)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True, verbose_name="Profil rasmi")
    
    def __str__(self):
        return self.user.username