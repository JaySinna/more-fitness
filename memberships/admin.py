from django.contrib import admin
from .models import Membership, Subscription, ExercisePlan, NutritionPlan

class MembershipAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'price', 'benefits')
    search_fields = ('name', 'benefits')
    list_filter = ('price',)

admin.site.register(Membership, MembershipAdmin)
admin.site.register(Subscription)
admin.site.register(ExercisePlan)
admin.site.register(NutritionPlan)