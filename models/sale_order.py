from odoo import api, models, fields
from odoo.exceptions import ValidationError

import logging
logger = logging.getLogger(__name__)

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'
    _description = 'Inherit Sale Order Module'

    nhis_number = fields.Char(string="NHIS Number")
    insurance_status = fields.Boolean(string="Insurance Status", default=False)
    payment_type = fields.Selection([
        ('cash', 'CASH'),
        ('insurance', 'INSURANCE'),
        ('free', 'FREE')
    ], string="Payment Type")
    external_visit_uuid = fields.Char(string="External Id")
    care_setting = fields.Selection([
        ('opd', 'OPD'),
        ('ipd', 'IPD')
    ])
    provider_name = fields.Char(string="Provider Name")
    claim_id = fields.Char(string="Claim Id")