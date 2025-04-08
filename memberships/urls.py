from django.urls import path
from . import views

urlpatterns = [
    path('', views.membership_list, name='membership_list'),
    path('subscribe/<int:membership_id>/', views.subscribe_to_membership, name='subscribe_to_membership'),
    path('success/', views.subscription_success, name='subscription_success'),
    path('exercise-plans/', views.exercise_plans, name='exercise_plans'),
    path('nutrition-plans/', views.nutrition_plans, name='nutrition_plans'),
    path('access-denied/', views.access_denied, name='access_denied'),
    path('exercise-plans/<int:pk>/', views.exercise_plan_detail, name='exercise_plan_detail'),
    path('nutrition-plans/<int:pk>/', views.nutrition_plan_detail, name='nutrition_plan_detail'),
    path('my-membership/', views.my_membership, name='my_membership'),
    path('membership-benefits/', views.membership_benefits, name='membership_benefits'),
    path('sample-plans/', views.sample_plans, name='sample_plans'),
]