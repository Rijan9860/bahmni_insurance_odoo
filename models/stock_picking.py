from odoo import api, models, fields

class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    sale_id = fields.Many2one('sale.order', string='Sale Order')
