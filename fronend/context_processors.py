# fronend/context_processors.py
from .models import AdminPremiumSettings

def cart_context(request):
    """Savat ma'lumotlarini barcha sahifalarga qo'shish"""
    cart_count = 0
    if request.user.is_authenticated:
        cart = request.session.get('savat', {})
        cart_count = len(cart)
    return {'cart_count': cart_count}

def premium_context(request):
    """Barcha sahifalarga premium ma'lumotlarni qo'shish"""
    context = {}
    
    # Premium sozlamalar
    try:
        settings = AdminPremiumSettings.get_settings()
        context['premium_settings'] = settings
        context['is_premium_enabled'] = settings.is_premium_enabled
    except:
        context['is_premium_enabled'] = False
    
    # Premium foydalanuvchi
    if request.user.is_authenticated:
        try:
            from .models import PremiumUser
            premium_profile = PremiumUser.objects.get(user=request.user)
            context['is_premium_user'] = premium_profile.is_premium and premium_profile.admin_approved
            context['can_add_premium'] = premium_profile.can_add_premium()
            context['premium_profile'] = premium_profile
            context['premium_remaining'] = premium_profile.get_remaining_premium_products()
        except:
            context['is_premium_user'] = False
            context['can_add_premium'] = False
    
    return context