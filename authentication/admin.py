from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profillar'

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    
    # Rozilik holatini ko'rsatish
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'terms_accepted')
    list_filter = ('profile__terms_accepted', 'is_staff', 'is_superuser', 'is_active')
    
    def terms_accepted(self, obj):
        try:
            return obj.profile.terms_accepted
        except Profile.DoesNotExist:
            return False
    terms_accepted.boolean = True
    terms_accepted.short_description = 'Shartlarga rozimi'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'terms_accepted', 'terms_accepted_at')
    list_filter = ('terms_accepted',)
    search_fields = ('user__username', 'user__email', 'phone')
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('user', 'birth_date', 'phone')
        }),
        ('Qoshimcha malumotlar', {
            'fields': ('secondary_phone', 'telegram', 'instagram', 'location', 'bio')
        }),
        ('Rozilik ma\'lumotlari', {
            'fields': ('terms_accepted', 'terms_accepted_at')
        }),
    )