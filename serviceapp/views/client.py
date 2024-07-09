import re

from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework import viewsets, status, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
import io, os
from PIL import Image
from serviceapp.models import Client, Bid
from serviceapp.serializers.bid_serializer import BidSerializer
from serviceapp.serializers.client_serializer import ClientSerializer
from serviceapp.views.helper import LogHelper, UserPermissions
from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required


class ClientView(APIView):
    permission_classes = (UserPermissions, )

    def get(self, request):
        clients = Client.objects.filter(created_by_id=request.user.id).order_by('id')
        serializer = ClientSerializer(clients, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs ):
        try:
            client_data = {
                "name": request.data['name'],
                "created_by_id": request.user.id
            }
            if 'email' in request.data:
                client_data['email'] = request.data['email']
            if 'phone' in request.data:
                client_data['phone'] = request.data['phone']
            if 'address' in request.data:
                client_data['address'] = request.data['address']
            Client.objects.create(**client_data)
            response = {
                "success": True,
                "message": "Client created successfully"
            }
            return Response(response, status=status.HTTP_201_CREATED)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["get"])
    @login_required
    def get_customers(request):
        response = {}
        try:
            if request.user.is_superuser:
                clients = Client.objects.all().order_by('id')
                paginator = PageNumberPagination()
                paginator.page_size = 10
                result_page = paginator.paginate_queryset(clients, request)
                serializer = ClientSerializer(result_page, many=True)
                return paginator.get_paginated_response(data=serializer.data)
            else:
                raise Exception
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["get"])
    @login_required
    def get_client_properties(request):
        response = {}
        try:
            if request.user.is_superuser:
                client_id = request.GET.get('customer_id')
                properties = Bid.objects.filter(client_id=client_id).order_by('-id')
                serializer = BidSerializer(properties, many=True)
                return Response(data=serializer.data, status=status.HTTP_200_OK)
            else:
                raise Exception
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please try again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


