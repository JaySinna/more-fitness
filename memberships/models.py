from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


class Membership(models.Model):
    BASIC = 'Basic'
    PREMIUM = 'Premium'

    MEMBERSHIP_CHOICES = [
        (BASIC, 'Basic'),
        (PREMIUM, 'Premium'),
    ]

    name = models.CharField(max_length=50, choices=MEMBERSHIP_CHOICES)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    benefits = models.TextField(default="No benefits listed", help_text="Comma separated list of membership benefits")
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name


class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE)
    stripe_subscription_id = models.CharField(max_length=255, null=True, blank=True)
    start_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.membership.name}"


class ExercisePlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name='exercise_plans'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_sample = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class NutritionPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name='nutrition_plans'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_sample = models.BooleanField(default=False)

    def __str__(self):
        return self.name
