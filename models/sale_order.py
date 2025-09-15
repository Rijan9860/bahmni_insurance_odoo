from odoo import api, models, fields
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'
    _description = 'Inherit Sale Order Module'

    nhis_number = fields.Char(string="NHIS Number")
    insurance_status = fields.Boolean(string="Insurance Status", default=False)
    payment_type = fields.Selection([
        ('cash', 'CASH'),
        ('insurance', 'INSURANCE'),
        ('free', 'FREE')
    ], string="Payment Type", default="cash")
    external_visit_uuid = fields.Char(string="External Id")
    care_setting = fields.Selection([
        ('opd', 'OPD'),
        ('ipd', 'IPD')
    ])
    provider_name = fields.Char(string="Provider Name")
    claim_id = fields.Char(string="Claim Id")
    shop_id = fields.Selection([
        ('registration', 'Registration'),
        ('pharmacy', 'Pharmacy')
    ], string="Shop", default="pharmacy")

    @api.onchange('payment_type')
    def _onchange_unit_price(self):
        if self.payment_type == "insurance":
            for rec in self.order_line:
                if rec.product_template_id:
                    _logger.info("Product Template Id---->%s", rec.product_template_id) 
                    insurance_odoo = self.env['insurance.odoo.product.map'].search([
                        ('odoo_product', '=', rec.product_template_id.id)
                    ]) 
                    if insurance_odoo:
                        rec.price_unit = insurance_odoo.insurance_product_price  
                        _logger.info("Insurance Odoo---->%s", rec.price_unit)     
        elif self.payment_type == "cash":
            for rec in self.order_line:
                product_template = self.env['product.template'].search([
                    ('id', '=', rec.product_template_id.id)
                ])
                if product_template:
                    rec.price_unit = product_template.list_price
        else:
            pass

    def action_confirm(self):
        _logger.info("Action Confrim Overwritten")
                    
class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'
    _description = 'Sale Order Line Inherit'
    
    payment_type = fields.Selection([
        ('cash', 'CASH'),
        ('insurance', 'INSURANCE'),
        ('free', 'FREE')
    ], string="Payment Type", related="order_id.payment_type", readonly=False)


                
