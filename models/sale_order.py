from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
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
    external_visit_uuid = fields.Char(string="External Id", help="This field is used to store visit ID of bahmni api call")
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
    partner_uuid = fields.Char(string="Customer UUID", store=True, readonly=True)
    discount_type = fields.Selection([
        ('nodiscount', 'No Discount'),
        ('percent', 'Percentage'),
        ('amount', 'Amount'),
        ],
        string="Discount Type",
        readonly=True,
        states={'draft': [('readonly', False)], 'sale':[('readonly', True)]},
        required=True,
        default="nodiscount"
    )
    discount_rate = fields.Float(string="Discount Rate", digits=dp.get_precision('Account'), default=0.00)
    discount_head = fields.Many2one('account.account', string="Discount Head", states={'draft': [('readonly', False)], 'sale': [('readonly', True)]})
    amount_untaxed = fields.Monetary(string="Untaxed Amount", store=True, readonly=True, tracking=True, compute="_amount_all")
    amount_tax = fields.Monetary(string="Taxes", store=True, readonly=True, tracking=True, compute="_amount_all")
    amount_total = fields.Monetary(string="Total", store=True, readonly=True, tracking=True, compute="_amount_all")
    amount_discount = fields.Monetary(string="Discount", store=True, readonly=True, digits=dp.get_precision('Amount'), tracking=True, compute="_amount_all")
    picking_ids = fields.One2many('stock.picking', 'sale_id', string='Transfers')

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """Compute the total amounts of the sale order"""
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_discount += (line.product_uom_qty * line.price_unit * line.discount) / 100
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_discount': amount_discount,
                'amount_total': amount_untaxed + amount_tax
            })
    
    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def _supply_rate(self):
        """supply discount into order line"""
        for order in self:
            if order.discount_type == "percent" and order.discount_rate > 0:
                for line in order.order_line:
                    line.discount = order.discount_rate
            elif order.discount_rate > 0:
                total = discount = 0.0
                for line in order.order_line:
                    total += (line.product_uom_qty * line.price_unit)
                if order.discount_rate != 0:
                    discount = (order.discount_rate / total) * 100
                else:
                    discount = order.discount_rate
                for line in order.order_line:
                    line.discount = discount
                    # new_sub_price = (line.price_unit * (discount / 100))
                    # line.total_discount = line.price_unit - new_sub_price
            if order.discount_type == "nodiscount":
                order.discount_rate = 0.00
    
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrderInherit, self)._prepare_invoice()
        if self.discount_type == "percent" or self.discount_type == "amount":
            discount_head_name = self.discount_head.code + " " + self.discount_head.name
            invoice_vals.update({
                'discount_type': self.discount_type,
                'discount_rate': self.discount_rate,
                'discount_head': discount_head_name,
                'amount_discount': self.amount_discount
            })
        else:
            invoice_vals.update({
                'discount_type': self.discount_type,
                'discount_rate': self.discount_rate,
                'amount_discount': self.amount_discount
            })
        return invoice_vals
   
    @api.onchange('payment_type')
    def _change_payment_type(self):
        for sale_order in self:
            if sale_order.payment_type == "cash":
                if sale_order.discount_type == "percent" or sale_order.discount_type == "amount":
                    _logger.info("########Entered#######")
                    discount_head_id = sale_order.env['account.account'].search([
                        ('code', '=', 1010001)
                    ]).id
                    if discount_head_id:
                        sale_order.discount_head = discount_head_id
                    else:
                        raise ValidationError("Discount head not found!!")
                for sale_order_line in sale_order.order_line:
                    product_template = sale_order.env['product.template'].search([
                        ('id', '=', sale_order_line.product_template_id.id)
                    ])
                    if product_template:
                        sale_order_line.price_unit = product_template.list_price
                    else:
                        raise ValidationError("Product Not Mapped!! Please Contact Admin.")
            elif sale_order.payment_type == "insurance":
                if sale_order.discount_type == "percent" or sale_order.discount_type == "amount":
                    _logger.info("########Entered#######")
                    discount_head_id = sale_order.env['account.account'].search([
                        ('code', '=', 1010002)
                    ])
                    if discount_head_id:
                        sale_order.discount_head = discount_head_id
                    else:
                        raise ValidationError("Discount head not found!!")
                for sale_order_line in sale_order.order_line:
                    if sale_order_line.product_template_id:
                        _logger.info("Product Template Id---->%s", sale_order_line.product_template_id) 
                        insurance_odoo = self.env['insurance.odoo.product.map'].search([
                            ('odoo_product_id', '=', sale_order_line.product_template_id.id)
                        ]) 
                        if insurance_odoo:
                            sale_order_line.price_unit = insurance_odoo.insurance_product_price 
                        else:
                            raise ValidationError("Product Not Mapped!! Please Contact Admin.")
            else:
                pass
    
    def action_confirm(self):
        _logger.info("#####Action Confrim Inherit#####")
        """ Confirm the given quotation(s) and set their confirmation date.

        If the corresponding setting is enabled, also locks the Sale Order.

        :return: True
        :rtype: bool
        :raise: UserError if trying to confirm locked or cancelled SO's
        """
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                "It is not allowed to confirm an order in the following states: %s",
                ", ".join(self._get_forbidden_state_confirm()),
            ))

        self.order_line._validate_analytic_distribution()

        for order in self:
            order.validate_taxes_on_sales_order()
            if order.partner_id in order.message_partner_ids:
                continue
            order.message_subscribe([order.partner_id.id])

        self.write(self._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()

        if self[:1].create_uid.has_group('sale.group_auto_done_setting'):
            # Public user can confirm SO, so we check the group on any record creator.
            self.action_done()

        """Pass lot/serial number value from sale order to stock picking model"""
        for sale_order in self:
            pickings = sale_order.picking_ids.filtered(
                lambda p: p.picking_type_code == "outgoing" and p.state not in ['done', 'cancel']
            )
            _logger.info("Pickings---->%s", pickings)

            for picking in pickings:
                for move in picking.move_ids_without_package:
                    sale_line = sale_order.order_line.filtered(lambda l: l.product_id == move.product_id and l.lot_id)
                    _logger.info("Sale Order line---->%s", sale_line)
                    if not sale_line:
                        _logger.warning("No matching sale line found for product %s in %s", move.product_id.display_name, sale_order.name)
                        continue

                    # If move lines exist, update them
                    if move.move_line_ids:
                        _logger.info("Updating move lines for product %s", move.product_id.display_name)
                        for ml in move.move_line_ids:
                            ml.lot_id = sale_line.lot_id
                            ml.qty_done = sale_line.product_uom_qty
                    else:
                        _logger.info("No move lines found for %s, skipping create.", move.product_id.display_name)

                # Validate the picking once all moves are updated
                picking.button_validate()
                _logger.info("Picking %s validated for Sale Order %s", picking.name, sale_order.name)
        
        for order in self:
            _logger.info("Sale Order Id:%s", order)
            self.action_invoice_create_commons(order)

        return True

    def action_invoice_create_commons(self, order):
        _logger.info("Inside action invoice create commons overwritten")
        for order in self:
            _logger.info("Sale Order Id:%s", order)
            self.env['insurance.claim']._create_claim(order)
            
class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'
    _description = 'Sale Order Line Inherit'
    
    payment_type = fields.Selection([
        ('cash', 'CASH'),
        ('insurance', 'INSURANCE'),
        ('free', 'FREE')
    ], string="Payment Type", related="order_id.payment_type", readonly=False)
    discount = fields.Float(string="Discount (%)", digits=(16, 2), default=0.0)
    lot_id = fields.Many2one('stock.lot', string="Batch No", store=True)
    # total_discount = fields.Float(string="Total Discount", default=0.0, store=True)
    expiration_date = fields.Datetime(string="Expiration Date", store=True, readonly=True)

    @api.onchange('lot_id')
    def _get_lot_expiration_date(self):
        for rec in self:
            if rec.product_id:
                if rec.lot_id:
                    stock_lot = self.env['stock.lot'].search([('id', '=', rec.lot_id.id)])
                    if stock_lot:
                        rec.expiration_date = stock_lot.expiration_date
                        _logger.info("Expiration Date---->%s", rec.expiration_date)
                    else:
                        raise ValidationError("Lot Not Matched!!")
                    
    @api.constrains('lot_id')
    def _check_lot(self):
        for rec in self:
            if rec.order_id.shop_id == "pharmacy":
                if rec.product_id:
                    if not rec.lot_id:
                        _logger.info("Lot Id is required for Storable Produts")
                        raise ValidationError("Lot Id is required for Storable Produts")
                    
                    
            
        
