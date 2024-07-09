import hashlib
import random
import re
import string
import pytz
from rest_framework.pagination import PageNumberPagination

from rest_framework.permissions import BasePermission
from rest_framework import viewsets, status, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
import io, os
from PIL import Image
from serviceapp.models import Users, ResetPassword
from serviceapp.serializers.user_serializer import UserSerializer
from serviceapp.views.helper import LogHelper
from rest_framework.decorators import api_view
from datetime import datetime, timedelta, date
from serviceapp.views.common import CommonView
from django.contrib.auth.hashers import make_password
from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction

from serviceapp.views.subscription import SubscriptionView


class UserProfilePermissions(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return True
        return False


class UserUploadPermissions(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return True
        elif request.method == 'POST':
            return True
        return False


class AdminPermissions(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return False


class UserViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    create:
    Create a new user instance.
    """
    queryset = Users.objects.all()
    serializer_class = UserSerializer
    permission_classes = (UserUploadPermissions,)

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                request.data['username'] = request.data['email']
                serializer = UserSerializer(data=request.data)
                if serializer.is_valid():
                    obj = serializer.save()
                    key = ''.join(
                        random.choice(string.ascii_letters + string.digits + string.ascii_letters) for _ in
                        range(10)) + str(datetime.now())
                    key = key.encode('utf-8')
                    verification_token = hashlib.sha224(key).hexdigest()
                    obj.email_verification_token = verification_token
                    obj.save()
                    start_date = datetime.today() + timedelta(days=14)
                    subscription = SubscriptionView.user_subscription(request, obj, start_date)
                    if not subscription['success']:
                        raise Exception
                    obj.is_subscribed = True
                    obj.save()
                    mail_template = "mails/registration_confirmation.html"
                    context = {
                        'key': verification_token
                    }
                    subject = "Roofbid ::Confirm Registration"
                    to = obj.email
                    CommonView.save_default_budgets(request, obj.id)
                    CommonView.save_default_contractor_info(request, obj)
                    CommonView.save_default_labor(request, obj.id)
                    CommonView.save_default_material(request, obj.id)
                    CommonView.save_default_roof_category(request, obj.id)
                    CommonView.send_email(request, mail_template, context, subject, to)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LogHelper.efail(e)
            return Response({'status': False, 'message': "Something went wrong."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserInfo(APIView):
    permission_classes = (UserProfilePermissions, )

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs ):
        try:
            updated_data = {}
            payload_data = request.data
            if 'first_name' in payload_data:
                updated_data['first_name'] = payload_data['first_name']
            if 'last_name' in payload_data:
                updated_data['last_name'] = payload_data['last_name']
            if 'phone' in payload_data:
                updated_data['phone'] = payload_data['phone']
            if 'company_description' in payload_data:
                updated_data['company_description'] = payload_data['company_description']
            if 'address' in payload_data:
                updated_data['address_1'] = payload_data['address']
            if 'contractor_types' in payload_data:
                updated_data['contractor_types'] = payload_data['contractor_types']
            if 'slopes' in payload_data:
                updated_data['slopes'] = payload_data['slopes']
            if 'roofs' in payload_data:
                updated_data['roofs'] = payload_data['roofs']
            if 'contractor_info' in payload_data:
                updated_data['contractor_info'] = payload_data['contractor_info']
            if 'default_budget' in payload_data:
                updated_data['default_budget'] = payload_data['default_budget']
            if 'close_out' in payload_data:
                updated_data['close_out'] = payload_data['close_out']

            Users.objects.filter(id=request.user.id).update(**updated_data)
            user = Users.objects.get(id=request.user.id)
            serializer = UserSerializer(user)
            # new_serializer_data = dict(serializer.data)
            # new_serializer_data['logo'] = CommonView.get_file_path(new_serializer_data['logo'])
            # new_serializer_data['logo_thumb'] = CommonView.get_file_path(new_serializer_data['logo_thumb'])
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "message": "Something went wrong. please try again"
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

    @api_view(["post"])
    @login_required()
    def upload_logo(request):
        try:
            updated_data = {}
            if 'logo' in request.FILES:
                logo = request.FILES['logo']
                logo_info = CommonView.handle_uploaded_file(logo, request.user)
                if 'path' in logo_info:
                    updated_data['logo'] = logo_info['path']
                    updated_data['logo_thumb'] = logo_info['thumb_path']
                    Users.objects.filter(id=request.user.id).update(**updated_data)
                    return Response({'status': True, 'message': "Logo upload successfully."}, status=status.HTTP_200_OK)
            return Response({'status': False, 'message': "Please attach logo file."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_404_NOT_FOUND)

    @api_view(["post"])
    @login_required()
    def update_subscription(request):
        try:
            user = Users.objects.get(id=request.user.id)
            user.address_1 = request.data['address_1']
            user.city = request.data['city']
            user.state = request.data['state']
            user.zip = request.data['zip']
            user.save()
            start_date = datetime.today()
            subscription = SubscriptionView.user_subscription(request, user, start_date)
            if not subscription['success']:
                raise Exception
            user.is_subscribed = True
            user.save()
            return Response({'status': True, 'message': "Subscription successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["post"])
    @login_required()
    def show_hide_one_time_setup(request):
        try:
            if 'show_initial_setup' in request.data:
                show_initial_setup = request.data['show_initial_setup']
                Users.objects.filter(id=request.user.id).update(one_time_setup=show_initial_setup)
                return Response({'status': True, 'message': "Settings Updated successfully."}, status=status.HTTP_200_OK)
            else:
                raise Exception
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_404_NOT_FOUND)


class ResetPasswordRequestViewSet:

    @api_view(["post"])
    def forget_password(request):
        try:
            response = {}
            email = request.data.pop("email", '')
            users = Users.objects.filter(email=email, is_active=1)
            if users.exists():
                user = users[0]
                current_time = datetime.now()
                expired_date = current_time + timedelta(hours=1)
                reset_code = user.resetpassword_set.filter(already_used=0, expired_at__gt=current_time)
                if reset_code.exists():
                    hash_code = reset_code[0].hash_code
                    ResetPassword.objects.filter(id=reset_code[0].id).update(expired_at=expired_date)
                else:
                    # generate hash code and store
                    key = ''.join(
                        random.choice(string.ascii_letters + string.digits + string.ascii_letters) for _ in
                        range(10)) + str(datetime.now())
                    key = key.encode('utf-8')
                    hash_code = hashlib.sha224(key).hexdigest()
                    ResetPassword(user=user, hash_code=hash_code, expired_at=expired_date).save()
                mail_template = "mails/reset_password.html"
                context = {
                    'key': hash_code
                }
                subject = "Roofbid ::Password Reset"
                to = user.email
                CommonView.send_email(request, mail_template, context, subject, to)
                response['success'] = True
                response['message'] = "A reset password email is sent to you with confirmation link"
                return Response(response, status=status.HTTP_200_OK)
            else:
                return Response({'success': False, 'message': "Email doesn't found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            LogHelper.efail(e)
            return Response({'success': False, 'message': "Something went wrong."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["post"])
    def change_user_password(request):
        try:
            if not request.user.is_authenticated:
                return Response({'success': False, 'message': "User not authorized."},
                                status=status.HTTP_401_UNAUTHORIZED)
            old_password = request.data.pop("old_password", '')
            password = request.data.pop("password", '')
            confirm_password = request.data.pop("confirm_password", '')
            if len(password) < 6:
                return Response({"password": "Password should be minimum 6 characters"}, status=status.HTTP_400_BAD_REQUEST)
            elif password != confirm_password:
                return Response({"password": "Passwords did not match"}, status=status.HTTP_400_BAD_REQUEST)
            if request.user.check_password(old_password):
                request.user.set_password(password)
                request.user.save()
            else:
                return Response({"old_password": "Old Passwords did not match"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'success': True, 'message': "Password Change Successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'success': False, 'message': "Something went wrong."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["get"])
    def email_verification(request):
        response = {}
        try:
            if request.user.is_authenticated:
                response['success'] = True
                response['message'] = "Already logged in"
                return Response(response, status=status.HTTP_200_OK)
            verification_code = request.GET["key"]
            user = Users.objects.get(email_verification_token=verification_code)
            if user.email_expired_at > date.today():
                user.is_active = True
                user.save()
                response['success'] = True
                response['message'] = "Email verified"
                return Response(response, status=status.HTTP_200_OK)
            else:
                response['success'] = False
                response['message'] = "Email authentication expired"
                return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ObjectDoesNotExist:
            response['success'] = False
            response['message'] = "Invaild token"
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please try again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResetPasswordView(APIView):
    def get(self, request, *args, **kwargs):
        hash_code = request.GET.get('key')
        response = {}
        try:
            reset_password = ResetPassword.objects.get(hash_code=hash_code)
            utc = pytz.UTC
            time_now = datetime.now().replace(tzinfo=utc)
            expired_at = reset_password.expired_at.replace(tzinfo=utc)
            if time_now > expired_at:
                raise PasswordResetException("expired")
            elif reset_password.already_used:
                raise PasswordResetException("used")
            else:
                user = reset_password.user
                response['success'] = True
                response['message'] = "Reset key is ok"
                response['hash_code'] = hash_code
                return Response(response, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            response['success'] = False
            response['message'] = "Not Found"
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except PasswordResetException as e:
            if e.message == 'expired':
                response['success'] = False
                response['message'] = "The link is already expired."
            elif e.message == 'used':
                response['success'] = False
                response['message'] = "The link is already used once by you."
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please try again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, *args, **kwargs):
        response = {}
        try:
            hash_code = request.data.pop("key", '')
            password = request.data.pop('password', '')
            confirm_password = request.data.pop('confirm_password', '')
            reset_password = ResetPassword.objects.get(hash_code=hash_code)
            user = reset_password.user
            utc = pytz.UTC
            time_now = datetime.now().replace(tzinfo=utc)
            expired_at = reset_password.expired_at.replace(tzinfo=utc)
            if time_now > expired_at:
                raise PasswordResetException("expired")
            elif reset_password.already_used:
                raise PasswordResetException("used")
            elif len(password) < 6:
                raise PasswordResetException("password_length")
            elif password != confirm_password:
                raise PasswordResetException("password_match")
            elif password == confirm_password:
                user.password = make_password(password)
                user.save()
                reset_password.already_used = True
                reset_password.save()
                response['success'] = True
                response['message'] = "Your password is changed successfully. You can now login"
                return Response(response, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            response['success'] = False
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except PasswordResetException as e:
            if e.message == 'expired':
                response['success'] = False
                response['message'] = "The link is already expired."
            elif e.message == 'used':
                response['success'] = False
                response['message'] = "The link is already used once by you."
            elif e.message == 'password_length':
                response['success'] = False
                response['message'] = "Password should be minimum 6 characters"
            elif e.message == 'password_match':
                response['success'] = False
                response['message'] = "Passwords did not match"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please try again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetException(Exception):
    def __init__(self, message):
        self.message = message


class ContractorView(APIView):
    permission_classes = (AdminPermissions, )

    def get(self, request):
        # if request.user.is_superuser:
        contractors = Users.objects.all().exclude(is_superuser=True).order_by('-id')
        paginator = PageNumberPagination()
        paginator.page_size = 10
        result_page = paginator.paginate_queryset(contractors, request)
        serializer = UserSerializer(result_page, many=True)
        return paginator.get_paginated_response(data=serializer.data)

    @api_view(["post"])
    @login_required
    def change_user_status(request):
        response = {}
        try:
            if request.user.is_superuser:
                user_id = request.data['user_id']
                is_active = request.data['active']
                user_data = Users.objects.filter(id=user_id).update(is_active=is_active)
                user = Users.objects.get(id=user_id)
                serializer = UserSerializer(user)
                return Response(data=serializer.data, status=status.HTTP_200_OK)
            else:
                raise Exception
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



