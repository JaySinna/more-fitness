from django.contrib import admin
from .models import Membership, Subscription, ExercisePlan, NutritionPlan

admin.site.register(Membership)
admin.site.register(Subscription)
admin.site.register(ExercisePlan)
admin.site.register(NutritionPlan)