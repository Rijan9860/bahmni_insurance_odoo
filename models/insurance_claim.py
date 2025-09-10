from odoo import api, models, fields
from odoo.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)

class InsuranceClaim(models.Model):
    _name = 'insurance.claim'
    _description = 'Insurance Claim Module'

    claim_code = fields.Char(string="Claim Code")