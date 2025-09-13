from odoo import api, models, fields
from odoo.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)

class InsuranceClaim(models.Model):
    _name = 'insurance.claim'
    _description = 'Insurance Claim Module'

    claim_code = fields.Char(string="Claim Code")
    partner_id = fields.Many2one('res.partner', string="Insuree")
    nhis_number = fields.Char(string="NHIS Number")
    nmc_number = fields.Char(string="NMC Number")
    care_setting = fields.Selection([
        ('opd', 'OPD'),
        ('ipd', 'IPD')
    ])
    claim_uuid = fields.Text(string="Claim UUID")
    creation_date = fields.Datetime(string="Creation Date")
    claims_manager = fields.Many2one('res.users', string="Claims Manager")
    insurance_claim_line = fields.One2many('insurance.claim.line', 'insurance_claim', string="Insurance Claim Line")
    sale_orders = fields.Many2many('sale.order', string="Sale Order")
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")

class InsuranceClaimLine(models.Model):
    _name = 'insurance.claim.line'
    _description = 'Insurance Claim Line Module'

    product_id = fields.Many2one('product.product', string="Product")
    imis_product_code = fields.Char(string="IMIS Product Code")
    quantity = fields.Integer(string="Qty")
    unit_price = fields.Float(string="Unit Price")
    total = fields.Monetary(string="Price Total", currency_field="currency_id")
    insurance_claim = fields.Many2one('insurance.claim', string="Insurace Claim")
    currency_id = fields.Many2one('res.currency', string="Currency")

