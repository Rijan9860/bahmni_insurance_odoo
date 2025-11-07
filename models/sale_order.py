from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
import odoo.addons.decimal_precision as dp
import requests
import base64
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
    claim_id = fields.Char(string="Claim Id")
    partner_uuid = fields.Char(string="Customer UUID", store=True, readonly=True)
   
    @api.onchange('payment_type')
    def _change_payment_type(self):
        for sale_order in self:
            if sale_order.payment_type == "cash":
                if sale_order.discount_type == "percentage" or sale_order.discount_type == "fixed":
                    _logger.info("########Entered#######")
                    discount_head_id = sale_order.env['account.account'].search([
                        ('code', '=', 450000)
                    ]).id
                    if discount_head_id:
                        sale_order.disc_acc_id = discount_head_id
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
                if sale_order.discount_type == "percentage" or sale_order.discount_type == "fixed":
                    _logger.info("########Entered#######")
                    discount_head_id = sale_order.env['account.account'].search([
                        ('code', '=', 1010002)
                    ])
                    if discount_head_id:
                        sale_order.disc_acc_id = discount_head_id
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

    def cap_validation(self):
        _logger.info("******Medicine Cap Validation******")
        nhis_number = self.nhis_number

        medicine_cap_url = "https://imis.hib.gov.np/api/api_fhir/cap-validation?CHFID={}".format(nhis_number)
        _logger.debug("Medicine Cap Url----->%s", medicine_cap_url)

        user_credentails = self.env['hib.config.settings'].search([('active', '=', 't')])
        username = ""
        password = ""
        remote_user = ""
        for rec in user_credentails:
            username = rec.username
            password = rec.password
            remote_user = rec.remote_user
        
        #Login Credentials
        login_data = {
            "username": username,
            "password": password,
            "remote_user": remote_user
        }

        #Encode Credentials
        credentials = "{}:{}".format(login_data["username"], login_data["password"])
        _logger.info("Credentials:%s", credentials)
        token = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        _logger.info("Token:%s", token)

        #Headers
        headers = {
            "remote-user": login_data["remote_user"],
            "Content-Type": 'application/json',
            "Authorization": "Basic {}".format(token)
        }

        _logger.info("Headers:%s", headers)

        # Send the GET request
        response = requests.get(medicine_cap_url, headers=headers)
        _logger.info("Response:%s", response)

        #Check if the request was successful 
        if response.status_code == 200:
            data = response.json()
            _logger.info("Cap Validation Results:%s", data)
            return data
        else:
            _logger.info("Error:%s", response.text)

    def check_eligibility(self):
        _logger.info("Check Eligibility")
        for rec in self:
            if rec.nhis_number:
                # cap_validation = self.cap_validation()
                # _logger.info("Cap Validation Data:%s", cap_validation)
                partner_id = rec.partner_id
                _logger.info("Partner Id:%s", partner_id)
                elig_response = self.env['insurance.eligibility'].get_insurance_details(partner_id)
                _logger.info("Eligibilty Response:%s", elig_response)
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Check Eligibilty',
                    'res_model': 'insurance.eligibility',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_id': elig_response.id,
                    'view_id': self.env.ref('bahmni_insurance_odoo.insurance_check_eligibility_response_view', False).id,
                    'target': 'new'
                }
            else:
                _logger.info("No NHIS number")
                raise UserError("No Insuree Id, Please update and retry !")   
  
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
        
        if self.payment_type == "insurance":
            for order in self:
                _logger.info("Sale Order Id:%s", order)
                self.action_invoice_create_commons(order)
        else:
            pass

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
                    
    # @api.constrains('lot_id')
    # def _check_lot(self):
    #     for rec in self:
    #         if rec.order_id.shop_id == "pharmacy":
    #             if rec.product_id:
    #                 if not rec.lot_id:
    #                     _logger.info("Lot Id is required for Storable Produts")
    #                     raise ValidationError("Lot Id is required for Storable Produts")
                    
                    
            
        
