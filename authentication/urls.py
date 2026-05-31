from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from django.conf.urls import include

urlpatterns = [
    
   # Auth URLs
    path('signup/', views.signup_view, name='signup'),
    path('kirish/', views.kirish_view, name='kirish'),
    path('chiqish/', views.chiqish_view, name='chiqish'),
 
    
    # Profile URLs
    path('settings/', views.settings_view, name='settings'),
    
    # API URLs (AJAX uchun)
  
    path('check-email/', views.check_email, name='check_email'),
    path('check-phone/', views.check_phone, name='check_phone'),
    path('update-profile-settings/', views.update_profile_settings, name='update_profile_settings'),
    path('update-password/', views.update_password, name='update_password'),
    path('update-notifications/', views.update_notifications, name='update_notifications'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)