from odoo import api, models, fields
from odoo.exceptions import ValidationError

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
    ], string="Payment Type")
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
    ])

    @api.onchange('shop_id')
    def _onchange_product(self):
        for rec in self:
            if rec.shop_id:
                _logger.info("Shop Id---->%s", rec.shop_id)
                product_template = self.env['product.template'].search([
                    ('shop_id', '=', rec.shop_id)
                ])
                _logger.info("Product Template---->%s", product_template)
                # for pt in product_template:
                #     _logger.info("asd---->%s", pt)
                #     if pt:
                #         rec.order_line.product_template_id = pt
                #         _logger.info("asd---->%s", rec.order_line.product_template_id)
                
