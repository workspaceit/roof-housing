from _datetime import datetime
import os
from datetime import timedelta

from django.views import generic
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from serviceapp.models import UserPaymentHistory
from serviceapp.util.authorize_dot_net import create_subscription_from_credit_card, cancel_subscription
from roofbid import settings
from serviceapp.views.common import CommonView
from serviceapp.views.helper import LogHelper
from django.contrib.auth.decorators import login_required


class SubscriptionView(generic.View):
    def user_subscription(request, user, start_date):
        response = {}
        try:
            subscription_description = 'RoofbidPro solo'
            user_data = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "expiration_year": request.data['expiration_year'],
                "expiration_month": request.data['expiration_month'],
                # "card_number": "4007000000027",
                "card_number": request.data['card_number'],
                "cvv": request.data['cvv']
            }
            payment_detail = {
                'card_holder_name': user_data['first_name'] + ' ' + user_data['last_name'],
                'card_number': str(user_data['card_number']),
                'expiration_date': user_data['expiration_year'] + '-' + user_data['expiration_month'],
                'card_code': str(user_data['cvv']),
                'amount': settings.MONTHLY_SUBSCRIPTION_FEE,
                'description': subscription_description + ' Monthly',
                'subscription_name': subscription_description + ' Monthly',
                'user_id': user.id,
                'email': user.email_address,
                'phone': user.phone,
                "address": user.address_1,
                "city": user.city,
                "state": user.state,
                "zip": user.zip,
                "country": user.country
            }
            # start_date = datetime.today()
            days = 30
            interval = request.data['subscription_type']
            if interval == "yearly":
                days = 365
                payment_detail['amount'] = settings.YEARLY_SUBSCRIPTION_FEE
                payment_detail['description'] = subscription_description + ' Annually'
                payment_detail['subscription_name'] = subscription_description + ' Annually'
            authorize_response = create_subscription_from_credit_card(payment_detail, start_date, days)
            if authorize_response['code'] == 200:
                data = {
                    'interval': interval,
                    'type': 'subscription',
                    'amount': payment_detail['amount'],
                    'payment_info': authorize_response,
                    'subscription_id': authorize_response['subscriptionId'],
                    'user_id': user.id
                }
                UserPaymentHistory.objects.create(**data)
                response['success'] = True
                response['data'] = data
            else:
                response['success'] = False
            return response
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            return response

    @api_view(['POST'])
    @login_required()
    def user_subscription_cancel(request):
        response = {}
        try:
            user_id = request.user.id
            subscribed_user = UserPaymentHistory.objects.filter(user__id=user_id, user__is_subscribed=True, is_active=True).first()
            subscription = SubscriptionView.cancel_subscription(request, subscribed_user, subscribed_user.subscription_id)
            if not subscription['success']:
                raise Exception
            response['success'] = True
            response['message'] = "Successfully UnSubscribed"
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            return Response({'success': False, 'message': "Something went wrong."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @api_view(['POST'])
    def webhook_subscription_failed_event(request):
        response = {}
        try:
            print("----------------Subscription webhook---------------")
            print(request.data)
            event_type = request.data['eventType']
            subscription_failed = 'net.authorize.customer.subscription.failed'
            subscription_cancelled = 'net.authorize.customer.subscription.cancelled'
            subscription_expired = 'net.authorize.customer.subscription.expired'
            subscription_suspended = 'net.authorize.customer.subscription.suspended'
            subscription_terminated = 'net.authorize.customer.subscription.terminated'
            events = [subscription_failed, subscription_cancelled, subscription_expired, subscription_suspended, subscription_terminated]
            if event_type in events:
                LogHelper.ilog(event_type)
                subscription_id = request.data['payload']['id']
                subscribed_user = UserPaymentHistory.objects.filter(subscription_id=subscription_id, user__is_subscribed=True, is_active=True)
                if subscribed_user.exists():
                    subscribed_user = subscribed_user[0]
                    '''
                    subscription canceled
                    '''
                    SubscriptionView.cancel_subscription(request, subscribed_user, subscription_id)
            else:
                LogHelper.ilog("Other Event")
            response['success'] = True
            response['message'] = "webhook"
            return Response(data=response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def cancel_subscription(request, subscribed_user, subscription_id):
        response = {
            'success': False
        }
        try:
            cancel_subscription(subscription_id)
            subscribed_user.is_active = False
            subscribed_user.save()
            subscribed_user.user.is_subscribed = False
            subscribed_user.user.save()
            LogHelper.ilog("Subscription cancelled")
            mail_template = "mails/subscription_cancelled.html"
            context = {}
            subject = "Roofbid ::Subscription Cancelled"
            to = subscribed_user.user.email
            CommonView.send_email(request, mail_template, context, subject, to)
            response['success'] = True
        except:
            LogHelper.ilog("not cancelled")
            pass
        return response

