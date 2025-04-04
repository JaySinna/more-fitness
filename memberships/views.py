from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from .models import Membership, Subscription
from profiles.models import UserProfile

def membership_list(request):
    """ A view to show all membership details """

    memberships = Membership.objects.all()
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