from django.http import HttpResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import User

from .models import Order, OrderLineItem
from products.models import Product
from profiles.models import UserProfile
from memberships.models import Membership, Subscription

import json
import time

import stripe

class StripeWH_Handler:
    """Handle Stripe webhooks"""

    def __init__(self, request):
        self.request = request

    def _send_confirmation_email(self, order):
        """Send the user a confirmation email"""
        cust_email = order.email
        subject = render_to_string(
            'checkout/confirmation_emails/confirmation_email_subject.txt',
            {'order': order})
        body = render_to_string(
            'checkout/confirmation_emails/confirmation_email_body.txt',
            {'order': order, 'contact_email': settings.DEFAULT_FROM_EMAIL})
        
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [cust_email]
        )

    def handle_event(self, event):
        """
        Handle a generic/unknown/unexpected webhook event
        """
        return HttpResponse(
            content=f'Unhandled webhook received: {event["type"]}',
            status=200)
    
    def handle_payment_intent_succeeded(self, event):
        """
        Handle the payment_intent.succeeded webhook from Stripe
        """
        intent = event.data.object
        pid = intent.id

        metadata = getattr(intent, 'metadata', {})
        bag = metadata.get('bag')
        save_info = metadata.get('save_info')
        username = metadata.get('username', 'AnonymousUser')

        try:
            stripe_charge = stripe.Charge.retrieve(intent.latest_charge)
        except Exception as e:
            return HttpResponse(
                content=f'Webhook received: {event["type"]} | ERROR retrieving charge: {e}',
                status=500
            )

        billing_details = stripe_charge.billing_details
        shipping_details = getattr(intent, 'shipping', None)
        grand_total = round(stripe_charge.amount / 100, 2)

        if shipping_details and shipping_details.address:
            for field, value in shipping_details.address.items():
                if value == "":
                    shipping_details.address[field] = None

        profile = None
        if username != 'AnonymousUser':
            try:
                profile = UserProfile.objects.get(user__username=username)
                if save_info and shipping_details:
                    profile.default_phone_number = shipping_details.phone
                    profile.default_country = shipping_details.address.country
                    profile.default_postcode = shipping_details.address.postal_code
                    profile.default_town_or_city = shipping_details.address.city
                    profile.default_street_address1 = shipping_details.address.line1
                    profile.default_street_address2 = shipping_details.address.line2
                    profile.default_county = shipping_details.address.state
                    profile.save()
            except UserProfile.DoesNotExist:
                profile = None

        if not bag:
            return HttpResponse(
                content=f'Webhook received: {event["type"]} | No bag found, skipping order creation.',
                status=200
            )

        order_exists = False
        attempt = 1
        order = None

        while attempt <= 5:
            try:
                order = Order.objects.get(
                    full_name__iexact=shipping_details.name,
                    email__iexact=billing_details.email,
                    phone_number__iexact=shipping_details.phone,
                    country__iexact=shipping_details.address.country,
                    postcode__iexact=shipping_details.address.postal_code,
                    town_or_city__iexact=shipping_details.address.city,
                    street_address1__iexact=shipping_details.address.line1,
                    street_address2__iexact=shipping_details.address.line2,
                    county__iexact=shipping_details.address.state,
                    grand_total=grand_total,
                    original_bag=bag,
                    stripe_pid=pid,
                )
                order_exists = True
                break
            except Order.DoesNotExist:
                attempt += 1
                time.sleep(1)

        if order_exists:
            self._send_confirmation_email(order)
            return HttpResponse(
                content=f'Webhook received: {event["type"]} | SUCCESS: Verified order already in database',
                status=200
            )

        try:
            order = Order.objects.create(
                full_name=shipping_details.name,
                user_profile=profile,
                email=billing_details.email,
                phone_number=shipping_details.phone,
                country=shipping_details.address.country,
                postcode=shipping_details.address.postal_code,
                town_or_city=shipping_details.address.city,
                street_address1=shipping_details.address.line1,
                street_address2=shipping_details.address.line2,
                county=shipping_details.address.state,
                grand_total=grand_total,
                original_bag=bag,
                stripe_pid=pid,
            )

            for item_id, item_data in json.loads(bag).items():
                product = Product.objects.get(id=item_id)
                if isinstance(item_data, int):
                    order_line_item = OrderLineItem(
                        order=order,
                        product=product,
                        quantity=item_data,
                    )
                    order_line_item.save()
                else:
                    for size, quantity in item_data['items_by_size'].items():
                        order_line_item = OrderLineItem(
                            order=order,
                            product=product,
                            quantity=quantity,
                            product_size=size,
                        )
                        order_line_item.save()

        except Exception as e:
            if order:
                order.delete()
            return HttpResponse(
                content=f'Webhook received: {event["type"]} | ERROR: {e}',
                status=500
            )

        self._send_confirmation_email(order)
        return HttpResponse(
            content=f'Webhook received: {event["type"]} | SUCCESS: Created order in webhook',
            status=200
        )
    
    def handle_payment_intent_payment_failed(self, event):
        """
        Handle the payment_intent.payment_failed webhook from Stripe
        """
        return HttpResponse(
            content=f'Webhook received: {event["type"]}',
            status=200)
    
    def handle_subscription_created(self, event):
        """
        Handle the customer.subscription.created webhook from Stripe
        """
        subscription = event['data']['object']
        customer_id = subscription['customer']
        subscription_id = subscription['id']
        metadata = subscription.get('metadata') or {}

        username = metadata.get('username')
        membership_id = metadata.get('membership_id')

        if not username or not membership_id:
            return HttpResponse(
                content='Missing username or membership_id in metadata.',
                status=400
            )

        try:
            user = User.objects.get(username=username)
            membership = Membership.objects.get(id=membership_id)

            Subscription.objects.create(
                user=user,
                membership=membership,
                stripe_subscription_id=subscription_id,
                is_active=True
            )

            profile = user.userprofile
            profile.stripe_customer_id = customer_id
            profile.stripe_subscription_id = subscription_id
            profile.is_member = True
            profile.save()

            return HttpResponse(
                content=f'Subscription created and linked to user {username}',
                status=200
            )

        except Exception as e:
            return HttpResponse(
                content=f'Error handling subscription.created: {str(e)}',
                status=500
            )

    def handle_subscription_payment_succeeded(self, event):
        """
        Handle the invoice.payment_succeeded webhook from Stripe
        """
        invoice = event['data']['object']
        subscription_id = invoice['subscription']
        customer_id = invoice['customer']
        amount_paid = invoice['amount_paid'] / 100
    
        try:
            profile = UserProfile.objects.get(stripe_customer_id=customer_id)
            profile.is_member = True
            profile.save()

            return HttpResponse(
                content=f'Successful payment for subscription {subscription_id}, membership updated.',
                status=200
            )
        except UserProfile.DoesNotExist:
            return HttpResponse(
                content=f'No user profile found for customer {customer_id}.',
                status=404
            )

    def handle_subscription_payment_failed(self, event):
        """
        Handle the invoice.payment_failed webhook from Stripe
        """
        invoice = event['data']['object']
        subscription_id = invoice['subscription']
        customer_id = invoice['customer']
    
        try:
            profile = UserProfile.objects.get(stripe_customer_id=customer_id)
            profile.is_member = False
            profile.save()

            self._send_payment_failure_email(profile)

            return HttpResponse(
                content=f'Payment failed for subscription {subscription_id}, membership flagged as inactive.',
                status=200
            )
        except UserProfile.DoesNotExist:
            return HttpResponse(
                content=f'No user profile found for customer {customer_id}.',
                status=404
            )
    
    def _send_payment_failure_email(self, profile):
        """
        Send a payment failure notification email to the user
        """
        subject = 'Payment Failed for Your Subscription'
        body = f'Dear {profile.user.username},\n\n' \
            'We were unable to process your subscription payment. Please update your payment information ' \
            'to continue enjoying your membership benefits.\n\n' \
            'If you have any questions, feel free to contact our support team.'
    
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [profile.user.email]
        )

    def handle_subscription_cancelled(self, event):
        """
        Handle the customer.subscription.deleted webhook from Stripe
        """
        subscription = event['data']['object']
        customer_id = subscription['customer']
        subscription_id = subscription['id']
    
        try:
            profile = UserProfile.objects.get(stripe_customer_id=customer_id)
            profile.is_member = False
            profile.save()

            return HttpResponse(
                content=f'Subscription cancelled: {subscription_id}, user membership updated.',
                status=200
            )
        except UserProfile.DoesNotExist:
            return HttpResponse(
                content=f'No user profile found for customer {customer_id}.',
                status=404
            )
        

    def handle_checkout_session_completed(self, event):
        """
        Handle the checkout.session.completed webhook from Stripe
        """
        print("🎯 Webhook endpoint was hit!")
        session = event['data']['object']
        metadata = session.get('metadata', {})
        print("DEBUG metadata:", metadata)

        customer_id = session.get('customer')
        subscription_id = session.get('subscription')

        username = metadata.get('username')
        membership_id = metadata.get('membership_id')

        if not username or not membership_id:
            print("❌ Missing metadata in checkout.session.completed")
            return HttpResponse(
                content='Missing metadata: username or membership_id',
                status=400
            )

        try:
            user = User.objects.get(username=username)
            profile = user.userprofile
            profile.stripe_customer_id = customer_id
            profile.stripe_subscription_id = subscription_id
            profile.is_member = True
            profile.save()

            membership = Membership.objects.get(id=membership_id)

            Subscription.objects.create(
                user=user,
                membership=membership,
                stripe_subscription_id=subscription_id,
                is_active=True,
            )

            print(f"✅ Subscription created for {username} with membership {membership_id}")
            return HttpResponse(
                content='Subscription created successfully from checkout.session.completed',
                status=200
            )

        except Exception as e:
            print("💥 Error in handle_checkout_session_completed:", str(e))
            return HttpResponse(
                content=f'Error in handle_checkout_session_completed: {str(e)}',
                status=500
            )