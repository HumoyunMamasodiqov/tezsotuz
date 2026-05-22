# fronend/forms.py
from django import forms
from .models import PremiumRequest
import re

class PremiumRequestForm(forms.ModelForm):
    class Meta:
        model = PremiumRequest
        fields = [
            'full_name', 
            'phone', 
            'telegram_username', 
            'email', 
            'requested_days', 
            'requested_limit', 
            'payment_method',
            'notes',
            'auto_approve',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ism va familiya'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '998XXXXXXXXX'
            }),
            'telegram_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '@ belgisiz kiriting'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@mail.com'
            }),
            'requested_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 365
            }),
            'requested_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 50
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Qo\'shimcha ma\'lumotlar...'
            }),
            'auto_approve': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'phone': 'Telefon raqami 998XXXXXXXXX formatida',
            'telegram_username': '@ belgisiz kiriting',
            'requested_days': 'Premium obuna davomiyligi (1-365 kun)',
            'requested_limit': 'Premium mahsulotlar soni (1-50 ta)',
        }
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Telefon raqamini tozalash
            cleaned_phone = re.sub(r'\D', '', phone)
            if len(cleaned_phone) == 9:
                cleaned_phone = f"998{cleaned_phone}"
            elif len(cleaned_phone) == 12 and cleaned_phone.startswith('998'):
                pass
            else:
                raise forms.ValidationError(
                    "Telefon raqami noto'g'ri formatda. 998XXXXXXXXX yoki 9XXXXXXXX formatida kiriting."
                )
            return cleaned_phone
        return phone
    
    def clean_telegram_username(self):
        telegram_username = self.cleaned_data.get('telegram_username')
        if telegram_username and telegram_username.startswith('@'):
            return telegram_username[1:]
        return telegram_username
    
    def clean_requested_days(self):
        days = self.cleaned_data.get('requested_days')
        if days and (days < 1 or days > 365):
            raise forms.ValidationError("Premium kunlari 1 dan 365 gacha bo'lishi kerak.")
        return days
    
    def clean_requested_limit(self):
        limit = self.cleaned_data.get('requested_limit')
        if limit and (limit < 1 or limit > 50):
            raise forms.ValidationError("Mahsulot limiti 1 dan 50 gacha bo'lishi kerak.")
        return limit