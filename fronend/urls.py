# urls.py - To'liq to'g'rilangan versiya

from django.urls import path
from . import views

urlpatterns = [
    # urls.py

path('api/search/advanced/', views.advanced_search, name='advanced_search'),
path('api/search/autocomplete/', views.search_autocomplete, name='search_autocomplete'),
path('api/search/popular/', views.get_popular_searches, name='popular_searches'),
    path('', views.home_view, name='home'),
    path('index/', views.index, name='index'),
        path('barcha-mahsulotlar/', views.barcha_mahsulotlar, name='barcha_mahsulotlar'), 
    path('kategoriya/<str:category_name>/', views.kategoriya_view, name='kategoriya'),
    path('baner/', views.baner, name='baner'),
    
    # Mahsulotlar
    path('mahsulot/<int:mahsulot_id>/', views.mahsulot_detail_view, name='mahsulot_detail'),
    path('premium-mahsulot/<int:mahsulot_id>/', views.premium_product_detail_view, name='premium_product_detail'),
    path('premium-mahsulotlar/', views.premium_products_view, name='premium_products'),
       path('premium-products/', views.premium_products_view, name='premium_products_en'),
    path('premium/check-before-request/', views.check_premium_before_request, name='check_premium_before_request'),
    
    # Premium so'rovni shu URL orqali ochish
    path('premium/request/', views.submit_premium_request_view, name='submit_premium_request'),
 
    # E'lon qo'shish
    path('elon-qoshish/', views.elon_qoshish_view, name='elon_qoshish'),
    path('add-premium-product/', views.add_premium_product_view, name='add_premium_product'),
    path('premium-check/', views.premium_product_check_view, name='premium_product_check'),
    
    # Premium so'rovlar
    path('submit-premium-request/', views.submit_premium_request_view, name='submit_premium_request'),
    path('my-premium-requests/', views.my_premium_requests_view, name='my_premium_requests'),
    path('cancel-premium-request/<int:request_id>/', views.cancel_premium_request_view, name='cancel_premium_request'),
    path('premium-request-detail/<int:request_id>/', views.premium_request_detail_view, name='premium_request_detail'),
    path('check-premium-status/', views.check_premium_status_view, name='check_premium_status'),

    path('admin/premium-dashboard/', views.admin_premium_dashboard, name='admin_premium_dashboard'),
    path('admin/premium-requests/', views.admin_premium_requests_view, name='admin_premium_requests'),
    path('admin/search-users/', views.admin_search_users_view, name='admin_search_users'),
    path('admin/process-premium-request/<int:request_id>/', views.admin_process_premium_request, name='admin_process_premium_request'),
    path('admin/extend-premium/<int:user_id>/', views.admin_extend_premium, name='admin_extend_premium'),
    path('admin/check-all-expired/', views.admin_check_all_expired, name='admin_check_all_expired'),
    path('admin/reset-premium-counter/<int:user_id>/', views.admin_reset_premium_counter, name='admin_reset_premium_counter'),
    path('admin/reactivate-premium/<int:user_id>/', views.admin_reactivate_premium, name='admin_reactivate_premium'),
    path('admin/set-premium-limit/<int:user_id>/', views.admin_set_premium_limit, name='admin_set_premium_limit'),
    path('admin/toggle-premium-product/<int:product_id>/', views.admin_toggle_premium_product, name='admin_toggle_premium_product'),
    path('admin/update-premium-settings/', views.admin_update_premium_settings, name='admin_update_premium_settings'),
    path('admin/premium-request-details/<int:request_id>/', views.admin_premium_request_details, name='admin_premium_request_details'),
   
   
    path('mening-elonlarim/', views.mening_elonlarim_view, name='mening_elonlarim'),
    path('sotilgan-qilish/<int:mahsulot_id>/', views.sotilgan_qilish_view, name='sotilgan_qilish'),
    path('yangi-qilish/<int:mahsulot_id>/', views.yangi_qilish_view, name='yangi_qilish'),
    path('elon-ochirish/<int:mahsulot_id>/', views.elon_ochirish_view, name='elon_ochirish'),
    
    # Profil
    path('my-profile/', views.my_profile_view, name='my_profile'),
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),
    path('user/<str:username>/', views.user_profile_view, name='user_profile'),
    
    
    
    # Sevimlilar
    path('sevimliga-qoshish/<int:mahsulot_id>/', views.sevimliga_qoshish_view, name='sevimliga_qoshish'),
    path('sevimlilarim/', views.sevimlilarim_view, name='sevimlilarim'),
    path('sevimlidan-ochirish/<int:sevimli_id>/', views.sevimlidan_ochirish_view, name='sevimlidan_ochirish'),
    
    # API va AJAX

path('api/search-suggestions/', views.api_search_suggestions, name='api_search_suggestions'),
path('api/search-popular/', views.api_search_popular, name='api_search_popular'),
    path('api/search/', views.api_search, name='api_search'),
    path('get-premium-status/', views.get_premium_status, name='get_premium_status'),
    path('make-product-premium/<int:product_id>/', views.make_product_premium, name='make_product_premium'),
    path('remove-product-premium/<int:product_id>/', views.remove_product_premium, name='remove_product_premium'),
    path('check-premium-access/', views.check_premium_access_view, name='check_premium_access'),
    
    # Admin kontakt
    path('admin-contact/', views.admin_contact_view, name='admin_contact'),
    
    # Cron
    path('cron/check-premium-expiry/', views.cron_check_premium_expiry, name='cron_check_premium_expiry'),
    
    # Boshqa sahifalar
    path('qosjso/', views.qosjso_view, name='qosjso'),
    path('bizhaqimizda/', views.bizhaqimizda_view, name='biz_haqimizda'),
    path('boglanish/', views.boglanish_view, name='boglanish'),
    path('test-404/', views.test_404, name='test_404'),
    path('newnav/', views.newnav, name='newnav'),
    path('kategoriya1/', views.kategoriya1, name='kategoriya1'),
    path('qoidalar/', views.qoidalar, name='qoidalar'),
    path('maxfiyliksiyosati/', views.maxfiyliksiyosati, name='maxfiyliksiyosati'),
    path('reklama/', views.reklama, name='reklama'),
]