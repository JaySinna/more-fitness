from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from .models import Membership, Subscription, ExercisePlan, NutritionPlan
from profiles.models import UserProfile


def membership_list(request):
    """ A view to show all membership details """

    memberships = Membership.objects.all()
    subscription = None

    if request.user.is_authenticated:
        user_profile = get_object_or_404(UserProfile, user=request.user)
        subscription = Subscription.objects.filter(user_profile=user_profile, is_active=True).first()

    context = {
        'memberships': memberships,
        'subscription': subscription,
    }

    return render(request, 'memberships/membership_list.html', context)


@login_required
def subscribe_to_membership(request, membership_id):
    """ Subscribe the logged-in user to the selected membership. """

    membership = get_object_or_404(Membership, id=membership_id)
    user_profile = get_object_or_404(UserProfile, user=request.user)

    subscription, created = Subscription.objects.get_or_create(
        user_profile=user_profile,
        defaults={'membership': membership}
    )

    if not created:
        subscription.membership = membership
        subscription.is_active = True
        subscription.save()

    return redirect('subscription_success')


def subscription_success(request):
    """A view to confirm successful subscription."""

    return render(request, 'memberships/subscription_success.html')


@login_required
def exercise_plans(request):
    """ Display exercise plans to subscribed users only. """

    user_profile = request.user.userprofile
    subscription = getattr(user_profile, 'subscription', None)

    if subscription and subscription.is_active:
        if subscription.membership.name.lower() == 'premium':
            plans = ExercisePlan.objects.filter(is_sample=False)
        else:
            plans = ExercisePlan.objects.filter(membership__name__iexact='basic', is_sample=False)

        context = {
            'plans': plans,
        }
        return render(request, 'memberships/exercise_plans.html', context)
    else:
        return render(request, 'memberships/access_denied.html')
    

@login_required
def nutrition_plans(request):
    """ Display nutrition plans to subscribed users only. """

    user_profile = request.user.userprofile
    subscription = getattr(user_profile, 'subscription', None)

    if subscription and subscription.is_active:
        if subscription.membership.name.lower() == 'premium':
            plans = NutritionPlan.objects.filter(is_sample=False)
        else:
            plans = NutritionPlan.objects.filter(membership__name__iexact='basic', is_sample=False)

        context = {
            'plans': plans,
        }
        return render(request, 'memberships/nutrition_plans.html', context)
    else:
        return render(request, 'memberships/access_denied.html')
    

def access_denied(request):
    """ Deny access to fitness plans to users without an active subscription. """

    return render(request, 'memberships/access_denied.html')


@login_required
def exercise_plan_detail(request, pk):
    """ Show detail for a single exercise plan if user's membership allows access. """

    plan = get_object_or_404(ExercisePlan, pk=pk)
    user_profile = request.user.userprofile
    subscription = getattr(user_profile, 'subscription', None)

    if subscription and subscription.is_active:
        if plan.membership == subscription.membership or subscription.membership.name.lower() == 'premium':
            context = {'plan': plan}
            return render(request, 'memberships/exercise_plan_detail.html', context)
        else:
            return render(request, 'memberships/access_denied.html')
    else:
        return render(request, 'memberships/access_denied.html')


@login_required
def nutrition_plan_detail(request, pk):
    """ Show detail for a single nutrition plan if user's membership allows access. """

    plan = get_object_or_404(NutritionPlan, pk=pk)
    user_profile = request.user.userprofile
    subscription = getattr(user_profile, 'subscription', None)

    if subscription and subscription.is_active:
        if plan.membership == subscription.membership or subscription.membership.name.lower() == 'premium':
            context = {'plan': plan}
            return render(request, 'memberships/nutrition_plan_detail.html', context)
        else:
            return render(request, 'memberships/access_denied.html')
    else:
        return render(request, 'memberships/access_denied.html')


def membership_benefits(request):
    """ Display the benefits of each membership. """
    
    memberships = Membership.objects.all()
    context = {
        'memberships': memberships,
    }
    return render(request, 'memberships/membership_benefits.html', context)


@login_required
def my_membership(request):
    """ Display the current subscription of the logged-in user. """

    user_profile = request.user.userprofile
    subscription = getattr(user_profile, 'subscription', None)

    if subscription and subscription.is_active:
        context = {
            'subscription': subscription,
        }
        return render(request, 'memberships/my_membership.html', context)
    else:
        return render(request, 'memberships/access_denied.html')
    

def sample_plans(request):
    """ Show example exercise and nutrition plans to non-members. """

    sample_exercise_plans = ExercisePlan.objects.filter(is_sample=True)
    sample_nutrition_plans = NutritionPlan.objects.filter(is_sample=True)

    context = {
        'sample_exercise_plans': sample_exercise_plans,
        'sample_nutrition_plans': sample_nutrition_plans,
    }
    return render(request, 'memberships/sample_plans.html', context)