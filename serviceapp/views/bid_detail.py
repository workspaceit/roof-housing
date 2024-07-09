import datetime
import json
import re

from django.db.models import Q
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


class BidDetailView(APIView):

    @api_view(["post"])
    @login_required()
    def create_proposal(request):
        try:
            payload_data = request.data
            proposal_dict = {
                "name": payload_data["name"],
                "proposal": payload_data["proposal"],
                "roof_category_id": payload_data['roof_category_id'],
                "bid_id": payload_data['bid_id']
            }
            proposal = BidProposal.objects.create(**proposal_dict)
            proposals_serializer = ProposalSerializer(proposal)
            response = {
                "success": True,
                "message": "Create proposal successfully",
                "proposal": proposals_serializer.data
            }
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["post"])
    @login_required()
    def update_proposal(request, proposal_id):
        try:
            payload_data = request.data
            proposal_data = BidDetailView.save_proposal(request, proposal_id, payload_data["proposal"])
            response = {
                "success": True,
                "message": "Update proposal successfully",
                "proposal": proposal_data['proposal']
            }
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["post"])
    @login_required()
    def update_budget(request, budget_id):
        try:
            payload_data = request.data
            budget_data = BidDetailView.save_budget(request, budget_id, payload_data["budget"])
            response = {
                "success": True,
                "message": "Update budget successfully",
                "budget": budget_data['budget']
            }
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["post"])
    @login_required()
    def update_job_cost(request, job_cost_id):
        try:
            payload_data = request.data
            job_cost = request.data['job_cost']
            job_cost_dict = {
                "work_order": job_cost["work_order"],
                "purchase_order": job_cost["purchase_order"],
                "equipment_order": job_cost["equipment_order"],
                "subcontractor_order": job_cost["subcontractor_order"]
            }
            job_cost = BidJobCost.objects.filter(id=job_cost_id).update(**job_cost_dict)
            job_cost_serializer = JobCostSerializer(BidJobCost.objects.get(id=job_cost_id))
            response = {
                "success": True,
                "message": "Update job cost successfully",
                "job_cost": job_cost_serializer.data
            }
            if 'budget' in request.data:
                budget_id = request.data['budget']['id']
                budget = request.data['budget']['budget']
                budget_data = BidDetailView.save_budget(request, budget_id, budget)
                response['budget'] = budget_data['budget']
            if 'proposal' in request.data:
                proposal_id = request.data['proposal']['id']
                proposal = request.data['proposal']['proposal']
                proposal_data = BidDetailView.save_proposal(request, proposal_id, proposal)
                response['proposal'] = proposal_data['proposal']
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def save_proposal(request, proposal_id, proposal):
        try:
            proposal_dict = {
                "proposal": proposal
            }
            proposal = BidProposal.objects.filter(id=proposal_id).update(**proposal_dict)
            proposals_serializer = ProposalSerializer(BidProposal.objects.get(id=proposal_id))
            response = {
                "success": True,
                "proposal": proposals_serializer.data
            }
            return response
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return response

    def save_budget(request, budget_id, budget):
        try:
            budget_dict = {
                "budget": budget
            }
            budget = BidBudget.objects.filter(id=budget_id).update(**budget_dict)
            budget_serializer = BudgetSerializer(BidBudget.objects.get(id=budget_id))
            response = {
                "success": True,
                "budget": budget_serializer.data
            }
            return response
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return response

    @api_view(["get"])
    @login_required()
    def get_proposal(request, proposal_id):
        try:
            proposal = BidProposal.objects.get(id=proposal_id)
            proposals_serializer = ProposalSerializer(proposal)
            response = {
                "success": True,
                "proposal": proposals_serializer.data
            }
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["get"])
    @login_required()
    def get_budget(request, budget_id):
        try:
            budget = BidBudget.objects.get(id=budget_id)
            budget_serializer = BudgetSerializer(budget)
            response = {
                "success": True,
                "budget": budget_serializer.data
            }
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @api_view(["get"])
    @login_required()
    def get_job_cost(request, job_cost_id):
        try:
            job_cost = BidBudget.objects.get(id=job_cost_id)
            job_cost_serializer = JobCostSerializer(job_cost)
            response = {
                "success": True,
                "job_cost": job_cost_serializer.data
            }
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            LogHelper.efail(e)
            response = {
                "success": False,
                "message": "Something went wrong. please try again"
            }
            return Response(data=response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
