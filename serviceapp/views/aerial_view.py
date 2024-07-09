import datetime
import math
import uuid
from http import HTTPStatus

import xmltodict
from django.core import mail
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from serviceapp.models import LaborType, RoofType, BidAerialOrder, Settings, BidDetail
from serviceapp.serializers.aerial_serializer import AerialAccountSerializer
from serviceapp.serializers.slope_serializer import LaborTypeSerializer, RoofTypeSerializer
from serviceapp.views.common import CommonView
from serviceapp.views.helper import LogHelper
from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required
import requests
import json
from django.conf import settings
from serviceapp.models import UserAerialAccount
from requests.structures import CaseInsensitiveDict

from serviceapp.views.mail import MailHelper


class AerialViewSet:

    @api_view(["post"])
    @login_required
    def login(request):
        response = {}
        try:
            username = request.data['username']
            password = request.data['password']
            source_id = settings.EAGLEVIEW_SOURCEID
            client_secret = settings.EAGLEVIEW_CLIENT_SECRET
            authorization_string = source_id + ":" + client_secret
            authorization_key = CommonView.make_base64(request, authorization_string)
            url = settings.EAGLEVIEW_ENDPOINT + "/Token"
            data = {'username': username, 'password': password, 'grant_type': 'password'}
            headers = {'Content-type': 'application/x-www-form-urlencoded',
                       'Authorization': 'Basic ' + authorization_key}
            r = requests.post(url, data=data, headers=headers)
            print("marchaint login status")
            print(r.status_code)
            print(r.__dict__)  
            if r.status_code == 200:
                token_info = json.loads(r.content.decode('ascii'))
                access_token = token_info['access_token']
                refresh_token = token_info['refresh_token']
                if not UserAerialAccount.objects.filter(user_id=request.user.id, vendor='eagleview').exists():
                    aerial_account_dict = {
                        "username": username,
                        "password": password,
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "token_info": token_info,
                        "user_id": request.user.id,
                        "endpoint": settings.EAGLEVIEW_ENDPOINT
                    }
                    UserAerialAccount.objects.create(**aerial_account_dict)
                else:
                    aerial_account_dict = {
                        "username": username,
                        "password": password,
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "token_info": token_info,
                        "is_active": True
                    }
                    UserAerialAccount.objects.filter(user_id=request.user.id, vendor='eagleview').update(**aerial_account_dict)
                response['success'] = True
                response['message'] = "Eagle view Login successfully"
                return Response(data=response, status=status.HTTP_200_OK)
            else:
                response['success'] = False
                response['message'] = "Login Failed"
                return Response(data=response, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # def merchant_login(request):
    #     response = {}
    #     try:
    #         merchant_settings = Settings.objects.all()
    #         username = None
    #         password = None
    #         source_id = None
    #         client_secret = None
    #         for setting in merchant_settings:
    #             if setting.key == 'eagleview_username' and setting.value != '':
    #                 username = setting.value
    #             if setting.key == 'eagleview_password' and setting.value != '':
    #                 password = setting.value
    #             if setting.key == 'eagleview_client_secret' and setting.value != '':
    #                 client_secret = setting.value
    #             if setting.key == 'eagleview_source_id' and setting.value != '':
    #                 source_id = setting.value
    #         authorization_string = source_id + ":" + client_secret
    #         authorization_key = CommonView.make_base64(request, authorization_string)
    #         url = settings.EAGLEVIEW_ENDPOINT + "/Token"
    #         data = {'username': username, 'password': password, 'grant_type': 'password'}
    #         headers = {'Content-type': 'application/x-www-form-urlencoded', 'Authorization': 'Basic ' + authorization_key}
    #         r = requests.post(url, data=data, headers=headers)
    #         if r.status_code == 200:
    #             token_info = json.loads(r.content.decode('ascii'))
    #             access_token = token_info['access_token']
    #             refresh_token = token_info['refresh_token']
    #             Settings.objects.filter(key='eagleview_access_token').update(value=access_token)
    #             Settings.objects.filter(key='eagleview_refresh_token').update(value=refresh_token)
    #             response['success'] = True
    #             response['access_token'] = access_token
    #             response['message'] = "Eagle view Login successfully"
    #         else:
    #             response['success'] = False
    #             response['message'] = "Login Failed"
    #         return response
    #     except Exception as e:
    #         LogHelper.efail(e)
    #         response['success'] = False
    #         response['message'] = "Something went wrong. Please tru again"
    #         return response

    @api_view(["get"])
    @login_required
    def aerial_profile(request):
        response = {}
        try:
            aerial_data = UserAerialAccount.objects.filter(user_id=request.user.id, vendor='eagleview', is_active=True).first()
            if not aerial_data:
                response['success'] = False
                response['message'] = "Not found"
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
            serializer = AerialAccountSerializer(aerial_data)
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["post"])
    @login_required
    def deactivate(request):
        response = {}
        try:
            UserAerialAccount.objects.filter(user_id=request.user.id, vendor='eagleview').update(is_active=False)
            response['success'] = True
            response['message'] = "Eagle view Deactivate successfully"
            return Response(data=response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def place_order(request, bid):
        response = {}
        response['success'] = False
        try:
            aerial_accounts = UserAerialAccount.objects.filter(user_id=request.user.id, vendor='eagleview', is_active=True)
            if aerial_accounts.exists():
                aerial_account = aerial_accounts[0]
                token = AerialViewSet.get_access_token_by_refresh_token(request, aerial_account)
                if token['success']:
                    access_token = token['token_info']['access_token']
                    order = AerialViewSet.order_request(request, access_token, bid)
                    print(order)
                    if order['success']:
                        order_info = {
                            "bid_id": bid.id,
                            "order_id": order['order_info']['OrderId'],
                            "report_id": order['order_info']['ReportIds'][0],
                            "ref_id": order['ref_id']
                        }
                        BidAerialOrder.objects.create(**order_info)
                        response['success'] = True
            return response
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return response

    def order_request(request, authorization_key, bid):
        response = {}
        try:
            # {
            #     "Address": "117 Queens Lane",
            #     "City": "Boydton",
            #     "State": "Virginia",
            #     "Zip": "23917",
            #     "Country": "USA",
            #     "Latitude": 37.263689698551204,
            #     "Longitude": -78.68216854472765,
            #     "AddressType": 4
            # }
            reference_number =  uuid.uuid4().hex[:16].lower()
            ref_id = "order-"+str(reference_number)
            data = {
                "OrderReports": [
                    {
                        "ReportAddresses": [
                            {
                                "Address": bid.address,
                                "City": bid.location['city'],
                                "State": bid.location['state'],
                                "Zip": bid.location['postal_code'],
                                "Country": bid.location['country'],
                                "Latitude": bid.location['latitude'],
                                "Longitude": bid.location['longitude'],
                                "AddressType": 4
                            }
                        ],
                        "PrimaryProductId": 31,
                        "DeliveryProductId": 8,
                        "MeasurementInstructionType": 2,
                        "ChangesInLast4Years": True,
                        "ReferenceId": ref_id
                    }
                ]
            }
            url = settings.EAGLEVIEW_ENDPOINT + "/v2/Order/PlaceOrder"
            headers = {'Content-type': 'application/json',
                       'Authorization': 'bearer ' + authorization_key}
            r = requests.post(url, data=json.dumps(data), headers=headers)
            if r.status_code == 200:
                order_info = json.loads(r.content.decode('ascii'))
                response['success'] = True
                response['message'] = "Order placed"
                response['order_info'] = order_info
                response['ref_id'] = ref_id
            else:
                response['success'] = False
                response['message'] = "Place order failed"
            return response
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return response

    def get_access_token_by_refresh_token(request, aerial_data):
        response = {}
        try:
            refresh_token = aerial_data.refresh_token
            source_id = settings.EAGLEVIEW_SOURCEID
            client_secret = settings.EAGLEVIEW_CLIENT_SECRET
            authorization_string = source_id + ":" + client_secret
            authorization_key = CommonView.make_base64(request, authorization_string)
            url = settings.EAGLEVIEW_ENDPOINT + "/Token"
            data = {'refresh_token': refresh_token, 'grant_type': 'refresh_token'}
            headers = {'Content-type': 'application/x-www-form-urlencoded',
                       'Authorization': 'Basic ' + authorization_key}
            r = requests.post(url, data=data, headers=headers)
            if r.status_code == 200:
                token_info = json.loads(r.content.decode('ascii'))
                access_token = token_info['access_token']
                refresh_token = token_info['refresh_token']
                token_info = token_info
                aerial_data.access_token = access_token
                aerial_data.refresh_token = refresh_token
                aerial_data.token_info = token_info
                aerial_data.save()
                response['success'] = True
                response['token_info'] = token_info
            else:
                response['success'] = False
            return response
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return response

    @api_view(["get"])
    def order_status_update(request):
        response = {
            "success": True,
            "message": "Success"
        }
        try:
            print(request.data)
            status_id = request.GET.get('StatusId')
            sub_status_id = request.GET.get('SubStatusId')
            ref_id = request.GET.get('RefId')
            report_id = request.GET.get('ReportId')
            LogHelper.ilog("Webhook called")
            LogHelper.ilog(report_id)
            LogHelper.ilog(status_id)
            LogHelper.ilog(sub_status_id)
            LogHelper.ilog(ref_id)
            aerial_order = BidAerialOrder.objects.filter(report_id=report_id).exclude(status="Completed").first()
            if aerial_order:
                if str(status_id) == "5":
                    aerial_accounts = UserAerialAccount.objects.filter(user_id=aerial_order.bid.created_by_id, vendor='eagleview',
                                                                       is_active=True)
                    if aerial_accounts.exists():
                        aerial_account = aerial_accounts[0]
                        token = AerialViewSet.get_access_token_by_refresh_token(request, aerial_account)
                        if token['success']:
                            access_token = token['token_info']['access_token']
                            report = AerialViewSet.get_report(request, access_token, report_id)
                            if not report['success']:
                                raise Exception
                            report_file = AerialViewSet.get_report_file(request, access_token, report_id)
                            if not report_file['success']:
                                raise Exception
                            aerial_order.report_url = report['report_url']
                            aerial_order.status = "Completed"
                            # aerial_order.updated_at = datetime.datetime.now()
                            aerial_order.save()
                            bid_detail = BidDetail.objects.filter(bid_id=aerial_order.bid_id).update(roof_lineal_footages=report['lineal_footage'], measurements=report_file['sections'])
                            AerialViewSet.save_others_data(request, report_file['sections'], aerial_order.bid_id)
                        else:
                            LogHelper.ilog("Eagleview Token not found")
                    else:
                        LogHelper.ilog("Aerial account not found")
                else:
                    LogHelper.ilog("Inprocess")
            else:
                LogHelper.ilog("No Order Found")
        except Exception as e:
            LogHelper.efail(e)
        return Response(response, status=status.HTTP_200_OK)

    @api_view(["post"])
    def file_delivery(request):
        response = {
            "success": True,
            "message": "Success"
        }
        try:
            print(request.data)
            ref_id = request.GET.get('RefId')
            report_id = request.GET.get('ReportId')
            file_format_id = request.GET.get('FileFormatId')
            file_type_id = request.GET.get('FileTypeId')
            LogHelper.ilog("Webhook called")
            LogHelper.ilog(report_id)
            LogHelper.ilog(file_format_id)
            LogHelper.ilog(file_type_id)
            LogHelper.ilog(ref_id)
            aerial_order = BidAerialOrder.objects.filter(report_id=report_id).exclude(status="Completed").first()
            if aerial_order:
                if str(file_type_id) == "107" and str(file_format_id) == "18":
                    aerial_accounts = UserAerialAccount.objects.filter(user_id=aerial_order.bid.created_by_id,
                                                                       vendor='eagleview',
                                                                       is_active=True)
                    if aerial_accounts.exists():
                        aerial_account = aerial_accounts[0]
                        token = AerialViewSet.get_access_token_by_refresh_token(request, aerial_account)
                        if token['success']:
                            access_token = token['token_info']['access_token']
                            report = AerialViewSet.get_report(request, access_token, report_id)
                            if not report['success']:
                                raise Exception
                            report_file = AerialViewSet.get_report_file(request, access_token, report_id)
                            if not report_file['success']:
                                raise Exception
                            aerial_order.report_url = report['report_url']
                            aerial_order.status = "Completed"
                            aerial_order.save()
                            bid_detail = BidDetail.objects.filter(bid_id=aerial_order.bid_id).update(
                                roof_lineal_footages=report['lineal_footage'], measurements=report_file['sections'])
                            AerialViewSet.save_others_data(request, report_file['sections'], aerial_order.bid_id)
                        else:
                            LogHelper.ilog("Eagleview Token not found")
                    else:
                        LogHelper.ilog("Aerial account not found")
                else:
                    LogHelper.ilog("Inprocess")
            else:
                LogHelper.ilog("No Order Found")
        except Exception as e:
            LogHelper.efail(e)
        return Response(response, status=status.HTTP_200_OK)

    @api_view(["post"])
    def get_aerial_data_manually(request):
        response = {
            "success": False,
            "message": "Aerial data is not ready yet"
        }
        try:
            print(request.data)
            bid_id = request.data['bid_id']
            report = BidAerialOrder.objects.filter(bid_id=bid_id).first()
            report_id = report.id
            LogHelper.ilog("Get data Manually")
            LogHelper.ilog(bid_id)
            aerial_order = BidAerialOrder.objects.filter(report_id=report_id).exclude(status="Completed").first()
            if aerial_order:
                aerial_data = AerialViewSet.get_aerial_order_data(request, aerial_order, report_id)
                if not aerial_data['success']:
                    raise Exception
            else:
                LogHelper.ilog("No Order Found")
        except Exception as e:
            LogHelper.efail(e)
            LogHelper.ilog("Inprocess")
        return Response(response, status=status.HTTP_200_OK)

    # def get_aerial_data_roofbid_get(request, bid_id):
    #     response = {
    #         "success": False,
    #         "message": "Aerial data is not ready yet"
    #     }
    #     try:
    #         print(request.data)
    #         report = BidAerialOrder.objects.filter(bid_id=bid_id).first()
    #         report_id = report.id
    #         LogHelper.ilog("Get roofbid aerial data")
    #         LogHelper.ilog(bid_id)
    #         aerial_order = BidAerialOrder.objects.filter(report_id=report_id).first()
    #         if aerial_order:
    #             aerial_data = AerialViewSet.get_aerial_order_data(request, aerial_order, report_id)
    #             if not aerial_data['success']:
    #                 raise Exception
    #             response['success'] = True
    #             response['message'] = 'Aerial data found'
    #         else:
    #             LogHelper.ilog("No Order Found")
    #     except Exception as e:
    #         LogHelper.efail(e)
    #         LogHelper.ilog("Inprocess")
    #     return response


    def get_aerial_order_data(request, aerial_order, report_id):
        response = {
            "success": False
        }
        try:
            aerial_accounts = UserAerialAccount.objects.filter(user_id=aerial_order.bid.created_by_id,
                                                               vendor='eagleview',
                                                               is_active=True)
            if aerial_accounts.exists():
                aerial_account = aerial_accounts[0]
                token = AerialViewSet.get_access_token_by_refresh_token(request, aerial_account)
                if token['success']:
                    access_token = token['token_info']['access_token']
                    report = AerialViewSet.get_report(request, access_token, report_id)
                    if not report['success']:
                        raise Exception
                    report_file = AerialViewSet.get_report_file(request, access_token, report_id)
                    if not report_file['success']:
                        raise Exception
                    aerial_order.report_url = report['report_url']
                    aerial_order.status = "Completed"
                    aerial_order.save()
                    bid_detail = BidDetail.objects.filter(bid_id=aerial_order.bid_id).update(
                        roof_lineal_footages=report['lineal_footage'], measurements=report_file['sections'])
                    AerialViewSet.save_others_data(request, report_file['sections'], aerial_order.bid_id)
                    response['success'] = True
                else:
                    LogHelper.ilog("Eagleview Token not found")
            else:
                LogHelper.ilog("Aerial account not found")
        except Exception as e:
            LogHelper.efail(e)
        return response

    def get_report(request, access_token, report_id):
        response = {
            "success": False
        }
        try:
            url = settings.EAGLEVIEW_ENDPOINT + "/v2/Report/GetReport?reportId=" + str(report_id) + ""
            print(url)
            headers = {'Authorization': 'bearer ' + access_token}
            r = requests.get(url, headers=headers)
            print(r.status_code)
            if r.status_code == 200:
                data = json.loads(r.content.decode('ascii'))
                print(data)
                e_lf = data['LengthEave'].split()[0]
                ridge_lf = data['LengthRidge'].split()[0]
                v_lf = data['LengthValley'].split()[0]
                r_lf = data['LengthRake'].split()[0]
                hip_lf = data['LengthHip'].split()[0]
                lineal_footage = {
                    "e_lf": e_lf,
                    "ridge_lf": ridge_lf,
                    "v_lf": v_lf,
                    "r_lf": r_lf,
                    "hip_lf": hip_lf,
                    "d_lf": "",
                    "h_lf": "",
                    "s_lf": "",
                    "v_method": ""
                }
                report_url = data['ReportDownloadLink']
                response['success'] = True
                response['lineal_footage'] = lineal_footage
                response['report_url'] = report_url
                print(response)
            return response
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return response

    def get_report_file(request, access_token, report_id):
        response = {
            "success": False
        }
        try:
            url = settings.EAGLEVIEW_ENDPOINT + "/v1/File/GetReportFile?reportId=" + str(
                report_id) + "&fileType=107&fileFormat=18"
            headers = {'Authorization': 'bearer ' + access_token}
            r = requests.get(url, headers=headers)
            print(url)
            print(r.status_code)
            if r.status_code == 200:
                data = json.loads(r.content.decode('utf-8'))
                faces = data['EAGLEVIEW_EXPORT']['STRUCTURES']['ROOF']['FACES']['FACE']
                sections = []
                for face in faces:
                    square = float(face['POLYGON']['@size'])/100
                    section_dict = {
                        "section": face['@designator'],
                        "pitch": face['POLYGON']['@pitch'],
                        "total_sq": round(square, 2)
                    }
                    sections.append(section_dict)
                response['success'] = True
                response['sections'] = sections
            print(response)
            return response
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return response

    def save_others_data(request, sections, bid_id):
        response = {
            "success": True
        }
        try:
            bid_detail = BidDetail.objects.get(bid_id=bid_id)
            actual_sq = 0
            for section in sections:
                actual_sq += float(section['total_sq'])
            actual_sq = round(actual_sq, 2)
            waste_percentage = 10
            waste_sq = round((actual_sq*waste_percentage)/100, 2)
            total_sq = float(math.ceil(actual_sq+waste_sq))
            bid_detail.others['extraActualSQ'] = actual_sq
            bid_detail.others['wastePercentage'] = waste_percentage
            bid_detail.others['extraWasteSQ'] = waste_sq
            bid_detail.others['extraTotalSQRoundUp'] = total_sq
            bid_detail.save()
        except Exception as e:
            LogHelper.efail(e)
        return response

    # @api_view(["post"])
    # def file_delivery(request):
    #     response = {
    #         "success": True,
    #         "message": "Success"
    #     }
    #     try:
    #         print(request.data)
    #     except Exception as e:
    #         LogHelper.efail(e)
    #     return Response(response, status=status.HTTP_200_OK)

    @api_view(["get"])
    def test_report(request):
        response = {
            "success": True,
            "message": "Success"
        }
        try:
            bid_detail = BidDetail.objects.get(bid_id=17)
            AerialViewSet.save_others_data(request, bid_detail.measurements, bid_detail.bid_id)
            return Response(response, status=status.HTTP_200_OK)
            report_id = 43392637
            access_token = "prI0bUKJC4QKMlUE03dR0YmFXg-U93ry2tAqrCGuA_3UMb40AoMOGymgIUl_okzP8zoXxh7-HmUFmv3z7F7hn3SCyWfizDOiHMBqG10iFRLVp6GBagHhVluycpO6GK-VRK2p2ppubwtTwxZagGCZm5jBK0MD6XH8XpzyJUWT4igxZCFvxNfmNy2uV8O1b02-dlYxqa3vWyBnvwZj2tPfnTKiCMIB5sDE0clZliYnAwUOFjbQ5YxZz2ROuwpFlnTF31FFjlmObSrndJv-3Jy2RK8q95y7uG67yC4xXxdsQ5G8JBMK454pu4pA-Y6pXhZ2Bmy35-LeL0vlhG3wK91QfXn715VIaFtSiaNcDQKEzWNb562bc6uKzfinjtzh_zi7DgWbkqeAilNbAzqmVOz79DPgUXZ7nJW49L8KiLK6IOmGE5owLY-ENlZplN67B0AS4uYtPq0fZleanLBIz_Sk2ns9vc6Ci_qcfpbmSR4gotlBJ4LfOCU2R70DxImG3yCBF7bl-NNlb69gJ-Y1hA4XnKyezTTdrg3Ni2osE02hWmmVLxzNLONJKnsElKBMOGPCepZi40TzqmVXZzrxtxPGm-SMD7mJfSUxnBT3RKZatsrjK4ZXhZfqivINjMDZqXKurBRCN9YCQmY9-kBeRocS1BXwnSI"
            report = AerialViewSet.get_report(request, access_token, report_id, None)
            report_file = AerialViewSet.get_report_file(request, access_token, report_id, None)
            print(report)
            print(report_file)
            # url = settings.EAGLEVIEW_ENDPOINT + "/v1/File/GetReportFile?reportId="+str(report_id)+"&fileType=18&fileFormat=4"
            # headers = {'Authorization': 'bearer ' + access_token}
            # r = requests.get(url, headers=headers)
            # print(r.status_code)
            # if r.status_code == 200:
            #     # print(r.content.decode('utf-8'))
            #     file_info = r.content.decode('utf-8')
            #     parsed_xml = xmltodict.parse(file_info, dict_constructor=dict)
            #     roof = parsed_xml['EAGLEVIEW_EXPORT']['STRUCTURES']['ROOF']
            #     faces = roof['FACES']['FACE']
            #     lines = roof['LINES']['LINE']
            #     points = roof['POINTS']['POINT']
            #     print(faces[0]['@id'])
            #     print(lines[0]['@path'])
            #     print(points[0]['@data'])
        except Exception as e:
            LogHelper.efail(e)
        return Response(response, status=status.HTTP_200_OK)

    @api_view(['GET'])
    def test_mail(request):
        try:
            print("Test mail")
            sender_mail = settings.EMAIL_HOST_USER
            print(sender_mail)
            import threading
            task = threading.Thread(target=MailHelper.mail_send, args=("test mail", "test", "mahedi@workspaceit.com", sender_mail))
            task.start()
            return JsonResponse({'status': True, 'data': "Success"}, status=HTTPStatus.OK)
        except Exception as e:
            print(e)
            return JsonResponse({'status': False, 'data': str(e)}, status=HTTPStatus.EXPECTATION_FAILED)
