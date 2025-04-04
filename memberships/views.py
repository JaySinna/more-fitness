from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from .models import Membership, Subscription
from profiles.models import UserProfile

def membership_list(request):
    """ A view to show all membership details """

    memberships = Membership.objects.all()

    context = {
        'memberships': memberships,
    }

    return render(request, 'memberships/membership_list.html', context)


@login_required
def subscribe_to_membership(request, membership_id):
    """ Subscribe the logged-in user to the selected membership. """

    membership = get_object_or_404(Membership, id=membership_id)
    user_profile = get_object_or_404(UserProfile, user=request.user)

    subscription, created = Subscription.objects.get_or_create(user_profile=user_profile)
    subscription.membership = membership
    subscription.is_active = True
    subscription.save()

    return redirect('membership_list')