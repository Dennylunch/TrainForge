from django.contrib import admin
from .models import UserDetail, Client, Exercise, ClientPlan, PlanExercise, Appointment, Subscription, UserExercise

admin.site.register(UserDetail)
admin.site.register(Client)
admin.site.register(Exercise)
admin.site.register(ClientPlan)
admin.site.register(PlanExercise)
admin.site.register(Appointment)
admin.site.register(UserExercise)

# custom models for admin panel
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_per_page = 7
    actions = ["archive_subscription", "unarchive_subscription"]
    
    def archive_subscription(self, request, queryset):
        queryset.update(is_archived=True)
    def unarchive_subscription(self, request, queryset):
        queryset.update(is_archived=False)
    def has_delete_permission(self, request, obj=None):
        return False
    
    archive_subscription.short_description = "Archive selected subscriptions"
    unarchive_subscription.short_description = "Unarchive selected subscriptions"