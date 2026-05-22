# authentication/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from .models import Profile
import re
import json

# ==================== AUTH VIEWS ====================

# authentication/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils.dateparse import parse_date
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.http import JsonResponse
from .models import Profile
import re

# authentication/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils.dateparse import parse_date
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.http import JsonResponse
from .models import Profile
import re

# ==================== SIGNUP VIEW ====================
@never_cache
def signup_view(request):
    """Ro'yxatdan o'tish sahifasi"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        # Ma'lumotlarni olish
        username = request.POST.get('username', '').strip()
        ism = request.POST.get('firstName', '').strip()
        familya = request.POST.get('lastName', '').strip()
        parol = request.POST.get('password', '').strip()
        tugilgan_sana = request.POST.get('birthDate', '').strip()
        telefon = request.POST.get('phone', '').strip()
        terms_accepted = request.POST.get('terms') == 'on'
        
        # Terms roziligini tekshirish
        if not terms_accepted:
            messages.error(request, "❗ Foydalanuvchi shartlariga rozilik bildirishingiz SHART!")
            return render(request, 'signup.html')
        
        # Username tekshirish
        if not username:
            messages.error(request, "Username (foydalanuvchi nomi) bo'sh bo'lishi mumkin emas!")
            return render(request, 'signup.html')
        
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Bu username allaqachon band! Iltimos, boshqa username tanlang.")
            return render(request, 'signup.html')
        
        # Boshqa maydonlarni tekshirish
        if not ism:
            messages.error(request, "Ism maydoni bo'sh bo'lishi mumkin emas.")
            return render(request, 'signup.html')
        if not familya:
            messages.error(request, "Familiya maydoni bo'sh bo'lishi mumkin emas.")
            return render(request, 'signup.html')
        if not parol:
            messages.error(request, "Parol maydoni bo'sh bo'lishi mumkin emas.")
            return render(request, 'signup.html')
        if not tugilgan_sana:
            messages.error(request, "Tug'ilgan sana maydoni bo'sh bo'lishi mumkin emas.")
            return render(request, 'signup.html')
        if not telefon:
            messages.error(request, "Telefon maydoni bo'sh bo'lishi mumkin emas.")
            return render(request, 'signup.html')

        # Telefonni formatlash
        clean_phone = re.sub(r'\D', '', telefon)
        if len(clean_phone) == 9:
            phone_formatted = f"+998{clean_phone}"
        elif len(clean_phone) == 12 and clean_phone.startswith('998'):
            phone_formatted = f"+{clean_phone}"
        else:
            messages.error(request, "Telefon raqam 9 xonali bo'lishi kerak (masalan: 901234567)")
            return render(request, 'signup.html')
        
        # Telefon unikalligini tekshirish
        if Profile.objects.filter(phone=phone_formatted).exists():
            messages.error(request, "Bu telefon raqami allaqachon ro'yxatdan o'tgan.")
            return render(request, 'signup.html')

        try:
            # Foydalanuvchi yaratish
            user = User.objects.create_user(
                username=username,
                first_name=ism,
                last_name=familya,
                email=f"{username}@tezsot.market",  # Avtomatik email yaratish
                password=parol,
                is_active=True
            )

            # Profil yaratish
            Profile.objects.create(
                user=user,
                birth_date=parse_date(tugilgan_sana),
                phone=phone_formatted,
                terms_accepted=True,
                terms_accepted_at=timezone.now()
            )

            # Avtomatik kirish
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {ism}!")
            return redirect('home')
                
        except Exception as e:
            messages.error(request, f"Ro'yxatdan o'tishda xatolik: {str(e)}")
            return render(request, 'signup.html')

    return render(request, 'signup.html')


# ==================== LOGIN VIEW ====================
@never_cache
def kirish_view(request):
    """Tizimga kirish sahifasi"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '').strip()
        
        user = None
        
        # 1. Username orqali qidirish
        try:
            user = User.objects.get(username__iexact=identifier)
        except User.DoesNotExist:
            pass
        
        # 2. Email orqali qidirish
        if user is None:
            try:
                user = User.objects.get(email__iexact=identifier)
            except User.DoesNotExist:
                pass
        
        # 3. Telefon orqali qidirish
        if user is None:
            clean_phone = re.sub(r'\D', '', identifier)
            if len(clean_phone) == 9:
                phone_formatted = f"+998{clean_phone}"
                try:
                    profile = Profile.objects.get(phone=phone_formatted)
                    user = profile.user
                except Profile.DoesNotExist:
                    pass
            elif len(clean_phone) == 12 and clean_phone.startswith('998'):
                phone_formatted = f"+{clean_phone}"
                try:
                    profile = Profile.objects.get(phone=phone_formatted)
                    user = profile.user
                except Profile.DoesNotExist:
                    pass

        if user is None:
            messages.error(request, "Foydalanuvchi topilmadi! Username, email yoki telefon raqamni tekshiring.")
            return render(request, 'kirish.html', {'identifier': identifier})

        # Parolni tekshirish
        user_auth = authenticate(request, username=user.username, password=password)
        if user_auth is None:
            messages.error(request, "Parol noto'g'ri!")
            return render(request, 'kirish.html', {'identifier': identifier})

        # Kirish muvaffaqiyatli
        login(request, user_auth)
        
        # Remember me
        if request.POST.get('remember_me'):
            request.session.set_expiry(1209600)  # 2 weeks
        else:
            request.session.set_expiry(0)
            
        messages.success(request, f"Xush kelibsiz, {user.first_name or user.username}!")
        return redirect('home')

    return render(request, 'kirish.html')


# ==================== LOGOUT VIEW ====================
@never_cache
def chiqish_view(request):
    """Tizimdan chiqish"""
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "Siz tizimdan muvaffaqiyatli chiqdingiz!")
    return redirect('kirish')


# ==================== HOME VIEW ====================
@never_cache
def home_view(request):
    """Bosh sahifa"""
    if not request.user.is_authenticated:
        return redirect('kirish')
    return render(request, 'home.html')


# ==================== CHECK USERNAME API ====================
def check_username(request):
    """Username bandligini tekshirish (AJAX)"""
    username = request.GET.get('username', '').strip()
    if username:
        exists = User.objects.filter(username__iexact=username).exists()
        return JsonResponse({'exists': exists})
    return JsonResponse({'exists': False})
# ==================== PROFILE VIEWS ====================

@never_cache
@login_required
def settings_view(request):
    """Sozlamalar sahifasi"""
    user = request.user
    
    # Profilni olish
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=user)
    
    context = {
        'user': user,
        'profile': profile,
        'seller_profile': profile,  # SellerProfile o'rniga Profile ishlatiladi
    }
    return render(request, 'settings.html', context)


@login_required
def update_profile_settings(request):
    """Profil ma'lumotlarini yangilash (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Noto\'g\'ri so\'rov'}, status=400)
    
    try:
        user = request.user
        profile = Profile.objects.get(user=user)
        
        # 1. User ma'lumotlarini yangilash
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('firstName', '').strip()
        last_name = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip()
        
        # Username o'zgartirish
        if username and username != user.username:
            if User.objects.exclude(id=user.id).filter(username__iexact=username).exists():
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Bu username allaqachon band! Iltimos, boshqa username tanlang.'
                }, status=400)
            user.username = username
        
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        
        if email and email != user.email:
            if User.objects.exclude(id=user.id).filter(email=email).exists():
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Bu email boshqa foydalanuvchida mavjud'
                }, status=400)
            user.email = email
        
        user.save()
        
        # 2. Profile ma'lumotlarini yangilash
        main_phone = request.POST.get('main_phone', '').strip()
        secondary_phone = request.POST.get('secondary_phone', '').strip()
        telegram = request.POST.get('telegram', '').strip()
        instagram = request.POST.get('instagram', '').strip()
        location = request.POST.get('location', '').strip()
        bio = request.POST.get('bio', '').strip()
        
        # Telefonni formatlash
        if main_phone:
            clean_phone = re.sub(r'\D', '', main_phone)
            if len(clean_phone) == 9:
                phone_formatted = f"+998{clean_phone}"
            elif len(clean_phone) == 12 and clean_phone.startswith('998'):
                phone_formatted = f"+{clean_phone}"
            else:
                return JsonResponse({'status': 'error', 'message': 'Noto\'g\'ri telefon formati'}, status=400)
            
            # Telefon unikalligi
            if Profile.objects.exclude(user=user).filter(phone=phone_formatted).exists():
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Bu telefon raqam boshqa foydalanuvchida mavjud'
                }, status=400)
            profile.phone = phone_formatted
        
        profile.secondary_phone = secondary_phone
        profile.telegram = telegram
        profile.instagram = instagram
        profile.location = location
        profile.bio = bio
        profile.save()
        
        # Profil rasmi (agar yuborilgan bo'lsa)
        if 'profile_image' in request.FILES:
            profile_image = request.FILES['profile_image']
            # Rasmni saqlash uchun (agar Profile modelida profile_image field bo'lmasa, SellerProfile ishlating)
            # profile.profile_image = profile_image
            # profile.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Profil ma\'lumotlari muvaffaqiyatli yangilandi!',
            'data': {
                'username': user.username,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'email': user.email,
                'main_phone': profile.phone,
                'secondary_phone': profile.secondary_phone or '',
                'telegram': profile.telegram or '',
                'instagram': profile.instagram or '',
                'location': profile.location or '',
                'bio': profile.bio or '',
            }
        })
        
    except Profile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Profil topilmadi'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def update_password(request):
    """Parolni yangilash (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Noto\'g\'ri so\'rov'}, status=400)
    
    try:
        old_password = request.POST.get('old_password', '')
        new_password1 = request.POST.get('new_password1', '')
        new_password2 = request.POST.get('new_password2', '')
        
        # Validatsiya
        if not old_password or not new_password1 or not new_password2:
            return JsonResponse({'status': 'error', 'message': 'Barcha maydonlarni to\'ldiring!'}, status=400)
        
        if new_password1 != new_password2:
            return JsonResponse({'status': 'error', 'message': 'Yangi parollar mos kelmadi!'}, status=400)
        
        if len(new_password1) < 8:
            return JsonResponse({'status': 'error', 'message': 'Parol kamida 8 ta belgidan iborat bo\'lishi kerak!'}, status=400)
        
        # Eski parolni tekshirish
        user = request.user
        if not user.check_password(old_password):
            return JsonResponse({'status': 'error', 'message': 'Joriy parol noto\'g\'ri!'}, status=400)
        
        # Parolni o'zgartirish
        user.set_password(new_password1)
        user.save()
        
        # Sessionni yangilash (foydalanuvchini chiqarib yubormaslik uchun)
        update_session_auth_hash(request, user)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Parol muvaffaqiyatli yangilandi!'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def update_notifications(request):
    """Bildirishnoma sozlamalarini yangilash"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Noto\'g\'ri so\'rov'}, status=400)
    
    try:
        data = json.loads(request.body)
        # Bildirishnoma sozlamalarini saqlash (agar modelda maydonlar bo'lsa)
        # profile = request.user.profile
        # profile.notifications_enabled = data.get('notifications', False)
        # profile.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Bildirishnoma sozlamalari saqlandi!'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ==================== CHECK USERNAME API ====================

def check_username(request):
    """Username bandligini tekshirish (AJAX)"""
    username = request.GET.get('username', '').strip()
    if username:
        exists = User.objects.filter(username__iexact=username).exists()
        return JsonResponse({'exists': exists})
    return JsonResponse({'exists': False})


def check_email(request):
    """Email bandligini tekshirish (AJAX)"""
    email = request.GET.get('email', '').strip()
    if email:
        exists = User.objects.filter(email__iexact=email).exists()
        return JsonResponse({'exists': exists})
    return JsonResponse({'exists': False})


def check_phone(request):
    """Telefon bandligini tekshirish (AJAX)"""
    phone = request.GET.get('phone', '').strip()
    if phone:
        clean_phone = re.sub(r'\D', '', phone)
        if len(clean_phone) == 9:
            phone_formatted = f"+998{clean_phone}"
        else:
            phone_formatted = phone
        
        exists = Profile.objects.filter(phone=phone_formatted).exists()
        return JsonResponse({'exists': exists})
    return JsonResponse({'exists': False})


# ==================== MY PROFILE VIEW ====================

@never_cache
@login_required
def my_profile_view(request):
    """Foydalanuvchi profili sahifasi"""
    user = request.user
    
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=user)
    
    return render(request, 'my_profile.html', {
        'user': user,
        'profile': profile,
    })