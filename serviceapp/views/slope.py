from rest_framework import status
from rest_framework.response import Response
from serviceapp.models import LaborType, RoofType
from serviceapp.serializers.slope_serializer import LaborTypeSerializer, RoofTypeSerializer
from serviceapp.views.helper import LogHelper
from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required


class SlopeViewSet:

    @api_view(["get"])
    @login_required
    def get_slopes(request):
        response = {}
        try:
            slopes = LaborType.objects.all()
            serializer = LaborTypeSerializer(slopes, many=True)
            response['success'] = True
            response['slopes'] = serializer.data
            return Response(data=response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["get"])
    @login_required
    def get_roofs(request):
        response = {}
        try:
            slope_id = request.GET['slope_id']
            roofs = RoofType.objects.filter(labor_type_id=slope_id, is_active=True).order_by('id')
            serializer = RoofTypeSerializer(roofs, many=True)
            response['success'] = True
            response['roofs'] = serializer.data
            return Response(data=response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
