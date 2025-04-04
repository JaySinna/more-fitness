from django.urls import path
from . import views

urlpatterns = [
    path('', views.membership_list, name='membership_list'),
    path('subscribe/<int:membership_id>/', views.subscribe_to_membership, name='subscribe_to_membership'),
    path('success/', views.subscription_success, name='subscription_success'),
]