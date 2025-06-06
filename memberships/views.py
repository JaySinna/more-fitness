from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Membership, Subscription, ExercisePlan, NutritionPlan
from profiles.models import UserProfile
import stripe
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponseRedirect


stripe.api_key = settings.STRIPE_SECRET_KEY


def membership_list(request):
    """ A view to show all membership details """

    memberships = Membership.objects.all()
    subscription = None

    if request.user.is_authenticated:
        subscription = Subscription.objects.filter(user=request.user, is_active=True).first()

    context = {
        'memberships': memberships,
        'subscription': subscription,
    }

    return render(request, 'memberships/membership_list.html', context)


@login_required
def subscribe_to_membership(request, membership_id):
    """ Redirect user to Stripe Checkout for subscription payment. """

    membership = get_object_or_404(Membership, id=membership_id)

    if not membership.stripe_price_id:
        messages.error(request, "Stripe Price ID is not set for this membership.")
        return redirect('membership_list')

    try:
        profile = request.user.userprofile

        metadata = {
            'username': request.user.username,
            'membership_id': str(membership.id),
        }

        if not profile.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                metadata=metadata
            )
            profile.stripe_customer_id = customer.id
            profile.save()
        else:
            stripe.Customer.modify(
                profile.stripe_customer_id,
                metadata=metadata
            )

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': membership.stripe_price_id,
                'quantity': 1,
            }],
            customer=profile.stripe_customer_id,
            metadata=metadata,
            success_url=request.build_absolute_uri(
                reverse('subscription_success', args=[membership.id])
            ),
            cancel_url=request.build_absolute_uri(
                reverse('membership_list')
            ),
        )

        return HttpResponseRedirect(checkout_session.url)

    except Exception as e:
        messages.error(request, f"Error creating checkout session: {str(e)}")
        return redirect('membership_list')


@login_required
def subscription_success(request, membership_id):
    """A view to confirm successful subscription."""

    membership = get_object_or_404(Membership, id=membership_id)

    context = {
        'membership': membership,
    }

    return render(request, 'memberships/subscription_success.html', context)


@login_required
def exercise_plans(request):
    """ Display exercise plans to subscribed users only. """
    subscription = Subscription.objects.filter(user=request.user, is_active=True).first()

    if subscription:
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
    subscription = Subscription.objects.filter(user=request.user, is_active=True).first()

    if subscription:
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


def exercise_plan_detail(request, pk):
    """ Show detail for a single exercise plan if user's membership allows access, or if it's a sample plan. """

    plan = get_object_or_404(ExercisePlan, pk=pk)

    # Allow access to sample plans for everyone
    if plan.is_sample:
        return render(request, 'memberships/exercise_plan_detail.html', {'plan': plan})

    if request.user.is_authenticated:
        subscription = Subscription.objects.filter(user=request.user, is_active=True).first()

        if subscription and (plan.membership == subscription.membership or subscription.membership.name.lower() == 'premium'):
            return render(request, 'memberships/exercise_plan_detail.html', {'plan': plan})

    return render(request, 'memberships/access_denied.html')


def nutrition_plan_detail(request, pk):
    """ Show detail for a single nutrition plan if user's membership allows access, or if it's a sample plan. """

    plan = get_object_or_404(NutritionPlan, pk=pk)

    # Allow access to sample plans for everyone
    if plan.is_sample:
        return render(request, 'memberships/nutrition_plan_detail.html', {'plan': plan})

    if request.user.is_authenticated:
        subscription = Subscription.objects.filter(user=request.user, is_active=True).first()

        if subscription and (plan.membership == subscription.membership or subscription.membership.name.lower() == 'premium'):
            return render(request, 'memberships/nutrition_plan_detail.html', {'plan': plan})

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

    subscription = Subscription.objects.filter(user=request.user, is_active=True).first()
    memberships = Membership.objects.all()

    context = {
        'memberships': memberships,
        'subscription': subscription,
    }

    return render(request, 'memberships/my_membership.html', context)


def sample_plans(request):
    """ Show example exercise and nutrition plans to non-members. """

    sample_exercise_plans = ExercisePlan.objects.filter(is_sample=True)
    sample_nutrition_plans = NutritionPlan.objects.filter(is_sample=True)

    context = {
        'sample_exercise_plans': sample_exercise_plans,
        'sample_nutrition_plans': sample_nutrition_plans,
    }
    return render(request, 'memberships/sample_plans.html', context)


@login_required
def unsubscribe(request, membership_id):
    """ Allow a logged-in user to unsubscribe from a membership. """

    user_profile = request.user.userprofile
    membership = get_object_or_404(Membership, id=membership_id)

    try:
        subscription = Subscription.objects.get(
            user=request.user,
            membership=membership,
            is_active=True
        )
    except Subscription.DoesNotExist:
        messages.error(request, 'No active subscription found for this membership.')
        return redirect('my_membership')

    if user_profile.stripe_subscription_id:
        try:
            stripe.Subscription.delete(user_profile.stripe_subscription_id)
        except Exception as e:
            messages.error(request, f'Error canceling subscription on Stripe: {str(e)}')
            return redirect('my_membership')

    subscription.is_active = False
    subscription.save()

    user_profile.is_member = False
    user_profile.stripe_subscription_id = None
    user_profile.save()

    messages.success(request, 'You have unsubscribed from your membership.')

    return redirect('my_membership')


@login_required
def confirm_unsubscribe(request, membership_id):
    """ Show confirmation page before unsubscribing """

    membership = get_object_or_404(Membership, id=membership_id)

    context = {
        'membership': membership,
    }

    return render(request, 'memberships/confirm_unsubscribe.html', context)


def newsletter_signup(request):
    """ A view to render the newsletter signup page """

    return render(request, 'memberships/newsletter_signup.html')
