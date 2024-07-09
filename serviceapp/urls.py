from rest_framework.routers import SimpleRouter
from django.conf.urls import url, include
from .views.users import UserViewSet, UserInfo, ResetPasswordRequestViewSet, ResetPasswordView, ContractorView
from .views.labor import LaborView
from .views.material import MaterialView
from .views.crew import CrewTeamView, CrewView
from .views.client import ClientView
from .views.bid import BidView
from .views.bid_detail import BidDetailView
from .views.slope import SlopeViewSet
from .views.aerial_view import AerialViewSet
from .views.subscription import SubscriptionView

router = SimpleRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    url(r'^auth/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    url(r'^user-profile/', UserInfo.as_view()),
    url(r'^upload-logo/', UserInfo.upload_logo),
    url(r'^labor/', LaborView.as_view()),
    url(r'^all-labor/', LaborView.get_all_labor),
    url(r'^material/', MaterialView.as_view()),
    url(r'^all-material/', MaterialView.get_all_material),
    url(r'^roof-sub-category/(?P<roof_type_id>[0-9]+)/', MaterialView.get_roof_sub_category),
    url(r'^all-roof-sub-category/', MaterialView.get_all_roof_sub_category),
    url(r'^create-proposal/', BidDetailView.create_proposal),
    url(r'^update-proposal/(?P<proposal_id>[0-9]+)/', BidDetailView.update_proposal),
    url(r'^update-budget/(?P<budget_id>[0-9]+)/', BidDetailView.update_budget),
    url(r'^update-job-cost/(?P<job_cost_id>[0-9]+)/', BidDetailView.update_job_cost),
    url(r'^get-proposal/(?P<proposal_id>[0-9]+)/', BidDetailView.get_proposal),
    url(r'^get-budget/(?P<budget_id>[0-9]+)/', BidDetailView.get_budget),
    url(r'^get-job-cost/(?P<job_cost_id>[0-9]+)/', BidDetailView.get_job_cost),
    url(r'^crew-team/', CrewTeamView.as_view()),
    url(r'^crew/', CrewView.as_view()),
    url(r'^update-crew/(?P<pk>[0-9]+)/', CrewView.update_crew),
    url(r'^delete-crew/(?P<pk>[0-9]+)/', CrewView.delete_crew),
    url(r'^client/', ClientView.as_view()),
    url(r'^customer/', ClientView.get_customers),
    url(r'^customer-properties/', ClientView.get_client_properties),
    url(r'^forget-password/', ResetPasswordRequestViewSet.forget_password),
    url(r'^reset-password/', ResetPasswordView.as_view()),
    url(r'^email-verification/', ResetPasswordRequestViewSet.email_verification),
    url(r'^change-user-password/', ResetPasswordRequestViewSet.change_user_password),
    url(r'^slopes/', SlopeViewSet.get_slopes),
    url(r'^roofs/', SlopeViewSet.get_roofs),
    url(r'^roofbid/', BidView.as_view()),
    url(r'^get-roofbid/(?P<pk>[0-9]+)/', BidView.get_roofbid),
    url(r'^update-roofbid/(?P<pk>[0-9]+)/', BidView.update_roofbid),
    url(r'^initial-settings/', UserInfo.show_hide_one_time_setup),
    url(r'^aerial/login/', AerialViewSet.login),
    url(r'^aerial/profile/', AerialViewSet.aerial_profile),
    url(r'^aerial/deactivate/', AerialViewSet.deactivate),
    url(r'^test-subscription/', SubscriptionView.user_subscription),
    url(r'^webhook-subscription-failed-event/', SubscriptionView.webhook_subscription_failed_event),
    url(r'^OrderStatusUpdate/', AerialViewSet.order_status_update),
    url(r'^FileDelivery', AerialViewSet.file_delivery),
    url(r'^contractors/', ContractorView.as_view()),
    url(r'^contractors-status/', ContractorView.change_user_status),
    url(r'^test-report/', AerialViewSet.test_report),
    url(r'^test-email/', AerialViewSet.test_mail),
    url(r'^cancel-subscription/', SubscriptionView.user_subscription_cancel),
    url(r'^update-subscription/', UserInfo.update_subscription),
    # url(r'^insert-sub-cat/', MaterialView.insert_sub_cat),

] + router.urls

