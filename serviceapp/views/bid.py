import datetime
import json
import re

from django.db.models import Q, Count
from rest_framework.permissions import BasePermission
from rest_framework import viewsets, status, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
import io, os
from PIL import Image
from serviceapp.models import Users, Bid, BidDetail, BidBudget, BidProposal, BidJobCost
from serviceapp.serializers.bid_serializer import BidDetailSerializer, BidSerializer
from serviceapp.serializers.budget_serializer import BudgetSerializer
from serviceapp.serializers.jobcost_serializer import JobCostSerializer
from serviceapp.serializers.proposal_serializer import ProposalSerializer
from serviceapp.views.aerial_view import AerialViewSet
from serviceapp.views.helper import LogHelper, UserPermissions
from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required
from rest_framework.pagination import PageNumberPagination
from collections import OrderedDict
from django.db import transaction


class CustomPagination(PageNumberPagination):
    def get_paginated_response(self, data, additional_field):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('bid_status_count', additional_field),
            ('results', data)
        ]))


class BidView(APIView):
    permission_classes = (UserPermissions, )

    def get(self, request):
        roofbid_filter = Q()
        roofbid_filter &= Q(created_by_id=request.user.id)
        order_by_filter = ['-id']
        if 'filter' in request.GET:
            current_filter = request.GET['filter']
            if current_filter == 'today':
                today = datetime.date.today()
                roofbid_filter &= Q(created_at__date=today)
            elif current_filter == 'week':
                current_week = datetime.date.today().isocalendar()[1]
                roofbid_filter &= Q(created_at__week=current_week)
            elif current_filter == 'month':
                current_month = datetime.date.today().month
                roofbid_filter &= Q(created_at__month=current_month)
        bid_status_count = Bid.objects.filter(roofbid_filter).aggregate(accepted=Count('pk', filter=Q(status='accepted')),
                                                                  completed=Count('pk', filter=Q(status='completed')),
                                                                  pending=Count('pk', filter=Q(status='pending')),
                                                                  total=Count('pk'))
        if 'group_by' in request.GET:
            group_by_filter = request.GET['group_by']
            if group_by_filter == 'status':
                order_by_filter.insert(0, 'status')
            elif group_by_filter == 'crew':
                order_by_filter.insert(0, 'crew_team_id')
        print(order_by_filter)
        # print(str(order_by_filter).strip('"[').strip(']"'))

        # order_string = str(order_by_filter).strip('"[').strip(']"')
        # for key, item in enumerate(order_by_filter):
        #     if key != 0 and key != len(order_by_filter):
        #         order_string += ', '
        #     order_string += "'"+ item +"'"
        # print(order_string)
        if 'status' in request.GET:
            status = request.GET['status']
            if status != 'all':
                roofbid_filter &= Q(status=status)
        bids = Bid.objects.filter(roofbid_filter).order_by(*order_by_filter)
        paginator = CustomPagination()
        paginator.page_size = 10
        result_page = paginator.paginate_queryset(bids, request)
        serializer = BidSerializer(result_page, many=True)
        data = serializer.data
        return paginator.get_paginated_response(data=data, additional_field=bid_status_count)

    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                # user = Users.objects.get(id=request.user.id)
                bid_data = {}
                payload_data = request.data
                if 'name' in payload_data:
                    bid_data['name'] = payload_data['name']
                bid_data['created_by_id'] = request.user.id
                if 'address' in payload_data:
                    bid_data['address'] = payload_data['address']
                if 'location' in payload_data:
                    bid_data['location'] = payload_data['location']
                bid_data['entry_type'] = payload_data['entry_type']
                if bid_data['entry_type'] == 'aerial':
                    bid_data['status'] = 'in_progress'
                bid = Bid.objects.create(**bid_data)
                bid_detail_data = {'bid_id': bid.id}
                bid_detail = BidDetail.objects.create(**bid_detail_data)
                # Block for test
                if bid_data['entry_type'] == 'aerial':
                    order = AerialViewSet.place_order(request, bid)
                    if not order['success']:
                        raise Exception
                serializer = BidSerializer(bid)
                response = {
                    "success": True,
                    "message": "Create Roofbid successfully",
                    "data": serializer.data
                }
                return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["get"])
    @login_required()
    def get_roofbid(request, pk):
        try:
            bid_detail = BidDetail.objects.filter(bid__created_by_id=request.user.id, bid_id=pk).first()
            serializer = BidDetailSerializer(bid_detail).data
            bid_serializer = BidSerializer(bid_detail.bid).data
            budgets = BidBudget.objects.filter(bid_id=pk)
            bid_budgets_serializer = BudgetSerializer(budgets, many=True).data
            job_costs = BidJobCost.objects.filter(bid_id=pk)
            bid_job_costs_serializer = JobCostSerializer(job_costs, many=True).data
            proposals = BidProposal.objects.filter(bid_id=pk)
            bid_proposals_serializer = ProposalSerializer(proposals, many=True).data
            response = {
                'data': {**serializer, **bid_serializer}
            }
            response['data']['budgets'] = bid_budgets_serializer
            response['data']['proposals'] = bid_proposals_serializer
            response['data']['job_costs'] = bid_job_costs_serializer
            return Response(data=response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_404_NOT_FOUND)

    @api_view(["post"])
    @login_required()
    def update_roofbid(request, pk):
        try:
            bid_detail = BidDetail.objects.get(bid_id=pk)
            payload_data = request.data
            if 'opportunity' in payload_data:
                bid_detail.opportunity = payload_data['opportunity']
            if 'project_manager' in payload_data:
                bid_detail.project_manager = payload_data['project_manager']
            if 'distributor' in payload_data:
                bid_detail.distributor = payload_data['distributor']
            if 'delevery_type' in payload_data:
                bid_detail.delevery_type = payload_data['delevery_type']
            if 'roof_details' in payload_data:
                bid_detail.roof_details = payload_data['roof_details']
            if 'roof_access' in payload_data:
                bid_detail.roof_access = payload_data['roof_access']
            if 'roof_lineal_footages' in payload_data:
                bid_detail.roof_lineal_footages = payload_data['roof_lineal_footages']
            if 'roof_quantites' in payload_data:
                bid_detail.roof_quantites = payload_data['roof_quantites']
            if 'skylight_quantites' in payload_data:
                bid_detail.skylight_quantites = payload_data['skylight_quantites']
            if 'solar_quantites' in payload_data:
                bid_detail.solar_quantites = payload_data['solar_quantites']
            if 'mechanical_quantites' in payload_data:
                bid_detail.mechanical_quantites = payload_data['mechanical_quantites']
            if 'measurements' in payload_data:
                bid_detail.measurements = payload_data['measurements']
            if 'others' in payload_data:
                bid_detail.others = payload_data['others']
            bid_detail.save()
            if 'client_id' in payload_data:
                bid_detail.bid.client_id = payload_data['client_id']
            if 'roofs' in payload_data:
                bid_detail.bid.roofs = payload_data['roofs']
            if 'date_entered' in payload_data:
                bid_detail.bid.date_entered = payload_data['date_entered']
            if 'date_expired' in payload_data:
                bid_detail.bid.date_expired = payload_data['date_expired']
            if bid_detail.bid.status == 'incomplete':
                bid_detail.bid.status = 'completed'
            if 'crew_team_id' in payload_data:
                bid_detail.bid.crew_team_id = payload_data['crew_team_id']
            if 'client_id' in payload_data:
                bid_detail.bid.client_id = payload_data['client_id']
            if 'status' in payload_data:
                bid_detail.bid.status = payload_data['status']
            bid_detail.bid.save()
            updated_bid_detail = BidDetail.objects.get(bid_id=pk)
            bid_detail_serializer = BidDetailSerializer(updated_bid_detail).data
            bid_serializer = BidSerializer(updated_bid_detail.bid).data
            serializer = {**bid_detail_serializer, **bid_serializer}
            if 'budgets' in payload_data:
                budgets = payload_data['budgets']
                if len(budgets) > 0:
                    bid_budgets = BidView.create_budgets(request, budgets, pk)
                    serializer['budgets'] = bid_budgets['budgets']
                else:
                    serializer['budgets'] = []

            if 'proposals' in payload_data:
                proposals = payload_data['proposals']
                if len(proposals) > 0:
                    bid_proposals = BidView.create_proposals(request, proposals, pk)
                    serializer['proposals'] = bid_proposals['proposals']
                else:
                    serializer['proposals'] = []
            if 'job_costs' in payload_data:
                job_costs = payload_data['job_costs']
                if len(job_costs) > 0:
                    bid_job_costs = BidView.create_job_costs(request, job_costs, pk)
                    serializer['job_costs'] = bid_job_costs['job_costs']
                else:
                    serializer['job_costs'] = []
            response = {
                "success": True,
                "message": "Update Roofbid successfully",
                "data": serializer
            }
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_404_NOT_FOUND)

    def create_budgets(request, budgets, bid_id):
        response = {
            "success": False
        }
        try:
            deleted_budgets = BidBudget.objects.filter(bid_id=bid_id).delete()
            budget_list = []
            for budget in budgets:
                budget_dict = {
                    # "approved_by": budget['approved_by'],
                    "budget": budget['budget'],
                    "roof_category_id": budget['roof_category_id'],
                    "bid_id": bid_id
                }
                budget_list.append(BidBudget(**budget_dict))
            bid_budgets = BidBudget.objects.bulk_create(budget_list)
            bid_budgets_serializer = BudgetSerializer(bid_budgets, many=True)
            response['success'] = True
            response['budgets'] = bid_budgets_serializer.data
            return response
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return response

    def create_proposals(request, proposals, bid_id):
        response = {
            "success": False
        }
        try:
            deleted_proposals = BidProposal.objects.filter(bid_id=bid_id).delete()
            proposal_list = []
            for proposal in proposals:
                proposal_dict = {
                    # "proposal_date": proposal['proposal_date'],
                    # "proposal_expires": proposal['proposal_expires'],
                    # "proposal_number": proposal['proposal_number'],
                    # "material_grade": proposal['material_grade'],
                    # "rating": proposal['rating'],
                    # "work_info": proposal['work_info'],
                    # "material_warranty": proposal['material_warranty'],
                    # "craftsman_warranty": proposal['craftsman_warranty'],
                    # "total_cost": proposal['total_cost'],
                    "name": proposal['name'],
                    "proposal": proposal["proposal"],
                    "roof_category_id": proposal['roof_category_id'],
                    "bid_id": bid_id
                }
                proposal_list.append(BidProposal(**proposal_dict))
            bid_proposals = BidProposal.objects.bulk_create(proposal_list)
            bid_proposals_serializer = ProposalSerializer(bid_proposals, many=True)
            response['success'] = True
            response['proposals'] = bid_proposals_serializer.data
            return response
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return response

    def create_job_costs(request, job_costs, bid_id):
        response = {
            "success": False
        }
        try:
            deleted_job_costs = BidJobCost.objects.filter(bid_id=bid_id).delete()
            job_cost_list = []
            for job_cost in job_costs:
                job_cost_dict = {
                    "work_order": job_cost['work_order'],
                    "purchase_order": job_cost['purchase_order'],
                    "equipment_order": job_cost['equipment_order'],
                    "subcontractor_order": job_cost['subcontractor_order'],
                    "roof_category_id": job_cost['roof_category_id'],
                    "bid_id": bid_id
                }
                job_cost_list.append(BidJobCost(**job_cost_dict))
            bid_job_costs = BidJobCost.objects.bulk_create(job_cost_list)
            bid_job_costs_serializer = JobCostSerializer(bid_job_costs, many=True)
            response['success'] = True
            response['job_costs'] = bid_job_costs_serializer.data
            return response
        except Exception as e:
            LogHelper.efail(e)
            response['success'] = False
            response['message'] = "Something went wrong. Please tru again"
            return response



