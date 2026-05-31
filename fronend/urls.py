# urls.py - To'liq to'g'rilangan versiya

from django.urls import path
from . import views
from . import admin_views
from . import purchase_views
from . import chat_views

urlpatterns = [
    # urls.py

path('api/search/advanced/', views.advanced_search, name='advanced_search'),
path('api/search/autocomplete/', views.search_autocomplete, name='search_autocomplete'),
path('api/search/popular/', views.api_search_popular, name='popular_searches'),
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

    # Cart va xarid
    path('savat/', purchase_views.view_cart, name='view_cart'),
    path('savatga-qoshish/<int:mahsulot_id>/', purchase_views.add_to_cart, name='add_to_cart'),
    path('savatdan-ochirish/<int:mahsulot_id>/', purchase_views.remove_from_cart, name='remove_from_cart'),
    path('savat-yangilash/<int:mahsulot_id>/', purchase_views.update_cart, name='update_cart'),
    path('rasmiylashtirish/', purchase_views.checkout, name='checkout'),
    path('mening-xaridlarim/', purchase_views.my_purchases, name='my_purchases'),
    path('sotuvlarim/', purchase_views.my_sales, name='my_sales'),
    path('buyurtma-holati/<int:purchase_id>/', purchase_views.update_purchase_status, name='update_purchase_status'),
    path('buyurtma-bekor/<int:purchase_id>/', purchase_views.cancel_purchase, name='cancel_purchase'),

    # Admin panel route (redirects to dashboard)
    path('admin-panel/', admin_views.admin_dashboard, name='admin_panel'),

    # Admin dashboard (new)
    path('admin-dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/products/', admin_views.admin_all_products, name='admin_all_products'),
    path('admin-dashboard/users/', admin_views.admin_all_users, name='admin_all_users'),
    path('admin-dashboard/toggle-product/<int:product_id>/', admin_views.admin_toggle_product_status, name='admin_toggle_product_status'),
    path('admin-dashboard/delete-product/<int:product_id>/', admin_views.admin_delete_product, name='admin_delete_product'),

    path('dashboard/premium/', views.admin_premium_dashboard, name='admin_premium_dashboard'),
    path('dashboard/premium-requests/', views.admin_premium_requests_view, name='admin_premium_requests'),
    path('dashboard/search-users/', views.admin_search_users_view, name='admin_search_users'),
    path('dashboard/process-premium-request/<int:request_id>/', views.admin_process_premium_request, name='admin_process_premium_request'),
    path('dashboard/extend-premium/<int:user_id>/', views.admin_extend_premium, name='admin_extend_premium'),
    path('dashboard/check-all-expired/', views.admin_check_all_expired, name='admin_check_all_expired'),
    path('dashboard/reset-premium-counter/<int:user_id>/', views.admin_reset_premium_counter, name='admin_reset_premium_counter'),
    path('dashboard/reactivate-premium/<int:user_id>/', views.admin_reactivate_premium, name='admin_reactivate_premium'),
    path('dashboard/set-premium-limit/<int:user_id>/', views.admin_set_premium_limit, name='admin_set_premium_limit'),
    path('dashboard/toggle-premium-product/<int:product_id>/', views.admin_toggle_premium_product, name='admin_toggle_premium_product'),
    path('dashboard/update-premium-settings/', views.admin_update_premium_settings, name='admin_update_premium_settings'),
    path('dashboard/premium-request-details/<int:request_id>/', views.admin_premium_request_details, name='admin_premium_request_details'),
    # Admin model management pages
    path('admin-models/banners/', admin_views.admin_banners, name='admin_banners'),
    path('admin-models/categories/', admin_views.admin_categories, name='admin_categories'),
    path('admin-models/sellers/', admin_views.admin_sellers, name='admin_sellers'),
    path('admin-models/favorites/', admin_views.admin_favorites, name='admin_favorites'),
    path('admin-models/notifications/', admin_views.admin_notifications_list, name='admin_notifications_list'),
    path('admin-models/premium-users/', admin_views.admin_premium_users_list, name='admin_premium_users_list'),
    path('admin-models/edit-contact/', admin_views.admin_contact_edit_view, name='admin_contact_edit'),
    path('admin-models/premium-settings/', admin_views.admin_premium_settings_view, name='admin_premium_settings_view'),
   
   
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
    
    # Premium, Banner, Featured sotib olish
    path('premium-sotib-olish/', purchase_views.buy_premium_view, name='buy_premium'),
    path('banner-sotib-olish/', purchase_views.buy_banner_view, name='buy_banner'),
    path('featured-sotib-olish/<int:product_id>/', purchase_views.buy_featured_view, name='buy_featured'),
    
    # Admin - Banner va Featured boshqaruvi
    path('admin-banner-xaridlari/', purchase_views.admin_banner_purchases, name='admin_banner_purchases'),
    path('admin-banner-tasdiqlash/<int:purchase_id>/', purchase_views.admin_banner_approve, name='admin_banner_approve'),
    path('admin-featured-xaridlari/', purchase_views.admin_featured_purchases, name='admin_featured_purchases'),
    path('admin-featured-tasdiqlash/<int:purchase_id>/', purchase_views.admin_featured_approve, name='admin_featured_approve'),
    
    # Foydalanuvchi mahsulot tanlashi (Featured/TOP uchun)
    path('top-uchun-mahsulot-tanlash/', purchase_views.select_product_for_featured, name='select_product_for_featured'),
    
    # Admin kontakt
    path('aloqa/', views.admin_contact_view, name='admin_contact'),
    
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
    
    # Chat
    path('chatlarim/', chat_views.my_chats, name='my_chats'),
    path('chat/<int:chat_id>/', chat_views.chat_detail, name='chat_detail'),
    path('chat/start/<int:product_id>/<int:seller_id>/', chat_views.start_chat, name='start_chat'),
    path('api/chat/send/<int:chat_id>/', chat_views.api_send_message, name='api_send_message'),
    path('api/chat/messages/<int:chat_id>/', chat_views.api_chat_messages, name='api_chat_messages'),
    path('api/chat/unread/', chat_views.api_unread_count, name='api_unread_count'),
    
    # Profil qidirish
    path('profil-qidirish/', views.profile_search_view, name='profile_search'),
    path('api/profile-search/', views.api_profile_search, name='api_profile_search'),
]