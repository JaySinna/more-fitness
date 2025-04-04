from django.shortcuts import render
from .models import Membership

def membership_list(request):
    """ A view to show all membership details """

    memberships = Membership.objects.all()

    context = {
        'memberships': memberships,
    }

    return render(request, 'memberships/membership_list.html', context)