from django.db import models
from PIL import Image
from imagekit.models import ProcessedImageField
from pilkit.processors import ResizeToFit
# Create your models here.
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser


from django.core.validators import FileExtensionValidator
from django.core.files.storage import FileSystemStorage
from django.contrib.postgres.fields import ArrayField
import shortuuid


def get_upload_path(instance, filename):
    """ creates unique-Path & filename for upload """
    ext = filename.split('.')[-1]
    image = Image.open(instance.photo)
    old_image = image
    output_image = io.BytesIO()
    image.save(output_image, old_image.format)
    filename = "%s.%s" % (instance.photo.name, ext)
    d = datetime.today()
    filename_with_path = 'public/images/' + d.strftime('%Y') + "/" + d.strftime('%m') + "/" + filename
    return filename_with_path


def generate_shortuuid():
    shortuuid.set_alphabet("abcdefghijklmnopqrstuvwxyz0123456789")
    guid = str(shortuuid.random(length=16))
    return guid


class Users(AbstractUser):
    # Personal info related fields
    email_address = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, null=True)
    company_description = models.CharField(max_length=256, null=True)
    address_1 = models.CharField(max_length=256, null=True)
    address_2 = models.CharField(max_length=256, null=True, blank=True)
    city = models.CharField(max_length=256, null=True)
    state = models.CharField(max_length=256, null=True)
    zip = models.CharField(max_length=256, null=True)
    country = models.CharField(max_length=256, null=True)
    logo = models.FileField(null=True, upload_to='logo/', validators=[FileExtensionValidator(allowed_extensions=['jpg','png','svg','jpeg'])], storage=FileSystemStorage())
    logo_thumb = models.FileField(null=True, upload_to='logo/', validators=[FileExtensionValidator(allowed_extensions=['jpg','png','svg','jpeg'])], storage=FileSystemStorage())
    contractor_types = ArrayField(models.CharField(max_length=50), default=list)
    slopes = ArrayField(models.IntegerField(), default=list)
    roofs = ArrayField(models.IntegerField(), default=list)
    default_budget = models.JSONField(default=list, null=True)
    contractor_info = models.JSONField(default=list, null=True)
    close_out = models.JSONField(default=list, null=True)
    email_verification_token = models.CharField(max_length=100, null=True)
    email_expired_at = models.DateField(null=True)
    one_time_setup = models.BooleanField(default=True, null=True)
    is_subscribed = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email_address'
    REQUIRED_FIELDS = ['username']

    def get_full_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    class Meta:
        db_table = "users"


class Client(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=256, null=True)
    phone = models.CharField(max_length=20, null=True)
    email = models.EmailField(max_length=50, null=True)
    created_by = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='client_created_by')
    # updated_by = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='client_updated_by', null=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'client'


class CrewTeam(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='crew_team_created_by')
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crew_team'


class Crew(models.Model):
    ACTION_CHOICE = (
        ('pm', 'PM'),
        ('foreman', 'Foreman'),
        ('installer', 'Installer'),
        ('demo', 'demo'),
        ('sales', 'Sales')
    )
    name = models.CharField(max_length=100)
    role = models.CharField(choices=ACTION_CHOICE, max_length=32)
    phone = models.CharField(max_length=20, null=True)
    email = models.EmailField(max_length=50, null=True)
    crew_team = models.ForeignKey(CrewTeam, on_delete=models.CASCADE)
    created_by = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='crew_created_by')
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crew'


class LaborType(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(null=True, auto_now_add=True)

    class Meta:
        db_table = 'labor_type'


class RoofType(models.Model):
    name = models.CharField(max_length=100)
    labor_type = models.ForeignKey(LaborType, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)

    class Meta:
        db_table = 'roof_type'

class RoofImage(models.Model):
    url = models.CharField(max_length=255)
    created_at = models.DateTimeField(null=True, auto_now_add=True)

    class Meta:
        db_table = 'roof_image'


class Labor(models.Model):
    ACTION_CHOICE = (
        ('to', 'Tear Off'),
        ('install', 'Install'),
        ('replace', 'Replace'),
        ('redeck', 'Redeck'),
        ('ec', 'Extra Charge'),
        ('rr', 'Remove and Replace'),
        ('bf', 'Build Curb and Flash'),
        ('flash', 'Flash'),
        ('rental', 'Rental'),
        ('mr', 'Month Rental'),
        ('dr', 'Detach and Reset'),
        ('layers', 'Layers')
    )
    CONVERSION_CHOICE = (
        ('ps', 'per SQ'),
        ('pb', 'per Board'),
        ('ea', 'EA'),
        ('pl', 'per LF'),
        ('each', 'Each'),
        ('quote', 'Quote'),
        ('ul', 'Unknown Layer')
    )
    TYPE_CHOICE = (
        ('to', 'Tear Off'),
        ('iu', 'INSTALL UNDERLAYMENT'),
        ('im', 'INSTALL MATERIAL'),
        ('ib', 'INSTALL BASE'),
        ('sl', 'STRUCTURAL LABOR'),
        ('elc', 'EXTRA LABOR CHARGES'),
        ('ec', 'EQUIPMENT CHARGES'),
        ('sc', 'SUBCONTRACTOR CHARGES'),
        ('cocp', 'CHANGE ORDER CHARGES ON PROPOSAL')
    )
    SLOPE_TYPE_CHOICE = (
        ('ss', 'Steep Slope'),
        ('ls', 'Low Slope'),
        ('both', 'Both')
    )
    action = models.CharField(choices=ACTION_CHOICE, max_length=32)
    type = models.CharField(choices=TYPE_CHOICE, max_length=32)
    slope_type = models.CharField(choices=SLOPE_TYPE_CHOICE, max_length=32)
    # roof_type = models.ForeignKey(RoofType, on_delete=models.CASCADE)
    description = models.CharField(max_length=100, null=True)
    roofs = ArrayField(models.IntegerField(), default=list)
    conversion = models.CharField(choices=CONVERSION_CHOICE, max_length=32)
    default_cost = models.FloatField()
    created_at = models.DateTimeField(null=True, auto_now_add=True)

    class Meta:
        db_table = 'labor'


class MaterialType(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)

    class Meta:
        db_table = 'material_type'


class Material(models.Model):
    CATEGORY_CHOICE = (
        ('stick', 'Stick'),
        ('plywood', 'Plywood'),
        ('decking', 'Decking'),
        ('underlayment', 'Underlayment'),
        ('roofing', 'Roofing'),
        ('tr', 'Tile Roofing'),
        ('ssr', 'SS Roofing'),
        ('scr', 'SCS Roofing'),
        ('lsr', 'Low Slope Roofing'),
        ('tile', 'Tile'),
        ('ss', 'Standing Seam'),
        ('scs', 'Stone Coated Steel'),
        ('felt', 'Felt'),
        ('sa', 'Self Adhered'),
        ('sam', 'SA Metal/Tile'),
        ('de', 'Drip Edge'),
        ('shingle', 'Shingle'),
        ('st', 'Shake/Tile'),
        ('sst', 'Shingle/Shake/Tile'),
        ('asphalt', 'Asphalt'),
        ('wood', 'Wood'),
        ('pb', 'Pipe Boot'),
        ('bv', 'Bathroom Vent'),
        ('av', 'Attic Vent'),
        ('skylight', 'Skylight'),
        ('torch', 'Torch'),
        ('insulation', 'Insulation'),
        ('taper', 'Taper'),
        ('recovery', 'Recovery'),
        ('mb', 'Modified Bitumen'),
        ('tpo', 'TPO'),
        ('adhesive', 'Adhesive'),
        ('primer', 'Primer'),
        ('sealant', 'Sealant'),
        ('cleaner', 'Cleaner'),
        ('coating', 'Coating'),
        ('eave', 'Eave'),
        ('wall', 'Wall'),
        ('parapet', 'Parapet'),
        ('drain', 'Drain'),
        ('vent', 'Vent')
    )
    description = models.CharField(max_length=100, null=True)
    category = models.CharField(choices=CATEGORY_CHOICE, max_length=32)
    type = models.ForeignKey(MaterialType, on_delete=models.CASCADE)
    roofs = ArrayField(models.IntegerField(), default=list, null=True)
    default_conversion = models.FloatField(null=True)
    default_cost = models.FloatField(null=True)
    image = models.ForeignKey(RoofImage, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)

    class Meta:
        db_table = 'material'


class UserLabor(models.Model):
    labor = models.ForeignKey(Labor, on_delete=models.CASCADE)
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    cost = models.FloatField(null=True)
    description = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_labor'


class UserMaterial(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    conversion = models.FloatField(null=True)
    description = models.CharField(max_length=100, null=True)
    cost = models.FloatField(null=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_material'


class UserRoofSubCategory(models.Model):
    roof_type = models.ForeignKey(RoofType, on_delete=models.CASCADE)
    material = models.ForeignKey(UserMaterial, on_delete=models.CASCADE)
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    created_at = models.DateTimeField(null=True, auto_now_add=True)

    class Meta:
        db_table = 'user_roof_sub_category'


class UserAerialAccount(models.Model):
    VENDOR_CHOICE = (
        ('eagleview', 'Eagle View'),
        ('test', 'Test View')
    )
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    vendor = models.CharField(choices=VENDOR_CHOICE, default="eagleview", max_length=32)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    endpoint = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    access_token = models.TextField(null=True)
    refresh_token = models.TextField(null=True)
    token_info = models.JSONField(default=dict, null=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'aerial_account'


class Bid(models.Model):
    STATUS_CHOICE = (
        ('in_progress', 'In Progress'),
        ('ready', 'Ready'),
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled')
    )
    ENTRY_CHOICE = (
        ('manual', 'Manual'),
        ('aerial', 'Aerial')
    )
    name = models.CharField(max_length=100, null=True)
    entry_type = models.CharField(ENTRY_CHOICE, default="manual", max_length=32)
    address = models.TextField(null=True)
    location = models.JSONField(default=dict)
    status = models.CharField(STATUS_CHOICE, default="in_progress", max_length=32)
    amount = models.FloatField(null=True, default=None)
    crew_team = models.ForeignKey(CrewTeam, on_delete=models.CASCADE, null=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True)
    roofs = ArrayField(models.IntegerField(), default=list)
    date_entered = models.DateField(null=True)
    date_expired = models.DateField(null=True)
    created_by = models.ForeignKey(Users, on_delete=models.CASCADE)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bid'


class BidDetail(models.Model):
    DELEVERY_TYPE_CHOICE = (
        ('gd', 'Ground Drop'),
        ('rl', 'Roof Load')
    )
    opportunity = models.CharField(max_length=255, null=True)
    project_manager = models.CharField(max_length=255, null=True)
    distributor = models.CharField(max_length=255, null=True)
    delevery_type = models.CharField(choices=DELEVERY_TYPE_CHOICE, max_length=32, null=True)
    roof_details = models.JSONField(default=list)
    roof_access = models.JSONField(default=list)
    roof_lineal_footages = models.JSONField(default=list)
    roof_quantites = models.JSONField(default=list)
    skylight_quantites = models.JSONField(default=list)
    solar_quantites = models.JSONField(default=list)
    mechanical_quantites = models.JSONField(default=list)
    measurements = models.JSONField(default=list)
    others = models.JSONField(default=list)
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE)

    class Meta:
        db_table = 'bid_detail'


class BidProposal(models.Model):
    # GRADE_CHOICE = (
    #     ('a', 'A'),
    #     ('b', 'B'),
    #     ('c', 'C'),
    #     ('d', 'D')
    # )
    # RATING_CHOICE = (
    #     ('ok', 'OK'),
    #     ('good', 'Good'),
    #     ('better', 'Better'),
    #     ('best', 'Best')
    # )
    name = models.CharField(max_length=255, null=True)
    proposal = models.JSONField(default=dict)
    # proposal_date = models.DateField()
    # proposal_expires = models.DateField()
    # proposal_number = models.CharField(max_length=100)
    # material_grade = models.CharField(choices=GRADE_CHOICE, max_length=32)
    # rating = models.CharField(choices=RATING_CHOICE, max_length=32)
    # work_info = models.JSONField(default=dict)
    # material_warranty = models.CharField(max_length=100)
    # craftsman_warranty = models.CharField(max_length=100)
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE)
    # total_cost = models.FloatField()
    roof_category = models.ForeignKey(UserRoofSubCategory, on_delete=models.CASCADE)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bid_proposal'


class BidBudget(models.Model):
    # approved_by = models.CharField(max_length=100, null=True)
    budget = models.JSONField(default=dict)
    roof_category = models.ForeignKey(UserRoofSubCategory, on_delete=models.CASCADE)
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bid_budget'


class BidJobCost(models.Model):
    work_order = models.JSONField(default=dict)
    purchase_order = models.JSONField(default=dict)
    equipment_order = models.JSONField(default=dict)
    subcontractor_order = models.JSONField(default=dict)
    roof_category = models.ForeignKey(UserRoofSubCategory, on_delete=models.CASCADE)
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bid_job_cost'


class ResetPassword(models.Model):
    hash_code = models.CharField(max_length=200)
    already_used = models.BooleanField(default=False)
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    expired_at = models.DateTimeField(default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reset_password"


class BidAerialOrder(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=50)
    report_id = models.CharField(max_length=50)
    ref_id = models.CharField(max_length=50)
    status = models.CharField(max_length=50, default="Inprocess")
    report_url = models.TextField(null=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bid_aerial_order'


class UserPaymentHistory(models.Model):
    TYPE_CHOICE = (
        ('subscription', 'Subscription'),
        ('payment', 'Payment')
    )
    INTERVAL_CHOICE = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    )
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    type = models.CharField(choices=TYPE_CHOICE, max_length=55, default='subscription')
    amount = models.FloatField()
    interval = models.CharField(choices=INTERVAL_CHOICE, max_length=55, default='monthly')
    payment_info = models.JSONField(default=dict)
    subscription_id = models.CharField(max_length=100, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_payment_history'
        verbose_name = "User Payment History"
        verbose_name_plural = "User Payment Histories"


class Settings(models.Model):
    key = models.CharField(max_length=255)
    value = models.TextField(null=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)

    class Meta:
        db_table = 'settings'