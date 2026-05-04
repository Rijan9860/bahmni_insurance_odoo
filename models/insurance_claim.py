from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
import requests
import pdfkit
import base64
import logging
_logger = logging.getLogger(__name__)

class InsuranceClaim(models.Model):
    _name = 'insurance.claim'
    _description = 'Insurance Claims'
    _order = "id desc"

    claim_code = fields.Char(string="Claim Code")
    claim_manager_id = fields.Many2one('res.users', string="Claims Manager", tracking=True)
    claimed_date = fields.Datetime(string="Creation Date", help="Claim Date")
    partner_id = fields.Many2one('res.partner', string="Insuree", required=True, tracking=True)
    nhis_number = fields.Char(string="NHIS Number")
    nmc_number = fields.Char(string="NMC Number")
    care_setting = fields.Selection([
        ('opd', 'OPD'),
        ('ipd', 'IPD'),
        ('emergency', 'Emergency')
    ])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('entered', 'Entered'),
        ('uploaded', 'Uploaded'),
        ('submitted', 'Submitted'),
        ('checked', 'Checked'),
        ('valuated', 'Valuated'),
        ('rejected', 'Rejected')
    ], string="State", default="draft")
    claim_uuid = fields.Text(string="Claim UUID")
    insurance_claim_line = fields.One2many('insurance.claim.line', 'claim_id', string="Insurance Claim Line")
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")
    external_visit_uuid = fields.Char(string="External Visit Id", help="This field is used to store visit id of a patient")
    partner_uuid = fields.Char(string="Customer UUID", store=True, readonly=True)
    sale_orders = fields.Many2many('sale.order', string="Sale Orders")
    currency_id = fields.Many2one(related="sale_orders.currency_id", string="Currency", store=True, readonly=True)
    icd_code = fields.Many2many('insurance.disease.code', string="Diagnosis", store=True)
    insurance_claim_history = fields.One2many('insurance.claim.history', 'claim_id', string="Claim Lines")
    claim_comments = fields.Text(string="Claim Comments")
    rejection_reason = fields.Text(string="Rejection Reason")

    def _create_claim(self, sale_order):
        _logger.info("Inside _create_claim")
        _logger.info("Sale Order Id:%s", sale_order)
        if sale_order and sale_order.payment_type in 'insurance':
            if not sale_order.nhis_number:
                raise ValidationError("Claim can't be created. NHIS Number is not present.")
        
            nmc_value = ""
            if sale_order.provider_name:
                nmc = sale_order.provider_name.split("_")
                if len(nmc) > 1:
                    nmc_value = nmc[1]
                    _logger.info("NMC Value:%s", nmc_value)
                else:
                    _logger.info("Invalid NMC Number")
            else:
                _logger.info("Provider Number is Empty")

            visit_uuid = sale_order.external_visit_uuid
            _logger.info("Visit UUID:%s", visit_uuid)

            if not visit_uuid:
                _logger.info("Visit UUID is Empty")

            insurance_number = sale_order.nhis_number
            claim_code = sale_order.claim_id

            claim = {
                'nhis_number': insurance_number,
                'claim_code': claim_code,
                'claim_manager_id': sale_order.user_id.id,
                'claimed_date': sale_order.create_date,
                'partner_id': sale_order.partner_id.id,
                'state': 'draft',
                'partner_uuid': sale_order.partner_uuid,
                'currency_id': sale_order.currency_id.id,
                'sale_orders': sale_order,
                'external_visit_uuid': visit_uuid,
                'care_setting': sale_order.care_setting,
                'nmc_number': nmc_value
            }
            _logger.info("Claim:%s", claim)
            claim_in_db = self.env['insurance.claim'].search([('external_visit_uuid', '=', visit_uuid), ('care_setting', '=', 'ipd'), ('state', '=', 'draft')])
            _logger.info("Existing IPD Claim Id:%s", claim_in_db)
            # Create a insurance claim
            if len(claim_in_db) == 0:
                _logger.info("*****Creating New Claim*****")
                claim_in_db = self.env['insurance.claim'].create(claim)
                _logger.info("Claim in db:%s", claim_in_db)

            # If care setting is "ipd" then adding new sales order
            _logger.info("New Sale Order Id:%s", sale_order)
            _logger.info("Old Sale Order Id:%s", claim_in_db.sale_orders)

            claim_in_db.update({
                'sale_orders': claim_in_db.sale_orders + sale_order
            })
            _logger.info("New Claim with added sale order:%s", claim_in_db)

            try:
                # Create a insurance claim line
                self._create_claim_line(claim_in_db, sale_order)

                insurance_claim_lines = self.env['insurance.claim.line'].search([
                    ('claim_id', '=', claim_in_db.id)
                ])

                _logger.info("Insurance Claim Line:%s", insurance_claim_lines)
                
                # Update 'insurance claim line' id in the insurance claim model
                if insurance_claim_lines:
                    claim_in_db.update({
                        'insurance_claim_line': insurance_claim_lines
                    })
                else:
                    _logger.info("No Claim Line Item Present")
                    raise ValidationError("No Claim Line Item Present")
                
                # Add history
                self._add_history(claim_in_db)
                
            except Exception as err:
                _logger.info("\n Error generating claim draft:%s", err)
                raise UserError(err)
            
            # To generate pdf report in the ir.attachment model
            _logger.info("Sale Order Name:%s", sale_order.name)
            account_move_id = self.env['account.move'].search([
                ('invoice_origin', '=', sale_order.name)
            ])
            _logger.info("Account Move Id:%s", account_move_id)
            claim_id = claim_in_db
            _logger.info("Claim Id:%s", claim_id)
            # self.env['account.move'].action_generate_attachment(account_move_id, claim_id)
        else:
            _logger.info("Payment Type:%s", sale_order.payment_type)
       
    def _create_claim_line(self, claim, sale_order):
        _logger.info("Inside _create_claim_line")
        insurance_sale_order_lines = sale_order.order_line.filtered(lambda l: l.payment_type == 'insurance')
        _logger.info("Insurance Sale Order Lines:%s", insurance_sale_order_lines)

        if not insurance_sale_order_lines:
            _logger.info("No sale order line found for insurance payment type")
            raise ValidationError("No sale order line found for insurance payment type")
        
        for sale_order_line in insurance_sale_order_lines:
            _logger.info("Inside insurance sale order line loop")
            imis_mapped_row = self.env['insurance.odoo.product.map'].search([
                ('odoo_product_id', '=', sale_order_line.product_id.id), 
                ('is_active', '=', True)
            ])
            _logger.info("IMIS Mapped Row:%s", imis_mapped_row)

            if not imis_mapped_row:
                raise ValidationError("IMIS Mapping not found for product:%s", sale_order_line.product_id.name)
            
            if len(imis_mapped_row) > 1:
                raise ValidationError("Multiple IMIS Mapping found for product:%s", sale_order_line.produt_id.name)
        
            #Check if a product is already present. If yes update the quantity.
            insurance_claim_line = claim.insurance_claim_line.filtered(lambda r: r.imis_product_code == imis_mapped_row.item_code)
            _logger.info("Insurance Claim Line:%s", insurance_claim_line)

            if insurance_claim_line:
                _logger.info("Insurance Claim Line Quantity:%s", insurance_claim_line.product_qty)
                insurance_claim_line.update({
                    'product_qty': insurance_claim_line.product_qty + sale_order_line.product_uom_qty
                })
                _logger.info("Insurance Claim Line After Adding Quantity:%s", insurance_claim_line.product_qty)
            else:
                self.create_new_claim_line(claim, sale_order_line, imis_mapped_row)

    def create_new_claim_line(self, claim, sale_order_line, imis_mapped_row):
        _logger.info("Inside create_new_claim_line")
        claim_line_item = {
            'claim_id': claim.id,
            'product_id': sale_order_line.product_id.id,
            'product_qty': sale_order_line.product_uom_qty,
            'imis_product': imis_mapped_row.id,
            'imis_product_code': imis_mapped_row.item_code,
            'price_unit': imis_mapped_row.insurance_product_price,
            'currency_id': claim.currency_id,
            'total': sale_order_line.price_subtotal
        }
        _logger.info("Claim Line Item:%s", claim_line_item)

        claim_line_in_db = self.env['insurance.claim.line'].create(claim_line_item)
        _logger.info("Claim Line in DB:%s", claim_line_in_db)

    def _add_history(self, claim_in_db):
        _logger.info("Inside _add_history")
        claim_history = self.env['insurance.claim.history']._add_claim_history(claim_in_db)
        _logger.info("Claim History=%s", claim_history)
        if claim_history:
            claim_in_db.update({
                'insurance_claim_history': claim_history
            })

    def action_retrieve_diagnosis(self):
        openmrs_connect_configurations = self.env['insurance.config.settings'].get_values()
        _logger.info("Openmrs Configuration=%s", openmrs_connect_configurations)
        if not openmrs_connect_configurations:
            raise UserError("OpenMRS Configuration Not Set!!")
        
        insurance_connect = self.env['insurance.connect']

        partner_uuid = self.partner_uuid
        _logger.info("Partner Uuid=%s", partner_uuid)
        external_visit_uuid = self.external_visit_uuid
        _logger.info("External Visit Uuid=%s", external_visit_uuid)

        url = insurance_connect.prepare_openmrs_url("/openmrs/ws/rest/v1/bahmnicore/diagnosis/search?patientUuid={}&visitUuid={}".format(partner_uuid, external_visit_uuid), openmrs_connect_configurations)
        _logger.info("URL=%s", url)
        custom_headers = {
            'Content-Type': 'application/json'
        }
        headers = insurance_connect.get_openmrs_header(openmrs_connect_configurations)
        custom_headers.update(headers)
        response = requests.get(url, headers=custom_headers, verify=False)
        _logger.info("Response=%s", response)

        if response.status_code == 200:
            resp = response.json()
            _logger.info("Resp=%s", resp)

            icd_codes_to_add = []

            for diagnosis in resp:
                mappings = diagnosis.get("codedAnswer", {}).get("mappings", [])
                for mapping in mappings:
                    if mapping.get("source") == 'ICD-11-WHO':
                        name = mapping.get("name")
                        code = mapping.get("code")
                        _logger.info("Name=%s", name)
                        _logger.info("Code=%s", code)

                        # search or create ICD code record
                        insurance_disease_code = self.env['insurance.disease.code'].search([('icd_code', '=', code)], limit=1)
                        _logger.info("Insurance Disease Code=%s", insurance_disease_code)

                        if not insurance_disease_code:
                            insurance_disease_code = self.env['insurance.disease.code'].create({
                                'diagnosis': name,
                                'icd_code': code
                            })
                        icd_codes_to_add.append(insurance_disease_code.id)
            # Update the many2many field
            if icd_codes_to_add:
                self.icd_code = [(4, icd_id) for icd_id in icd_codes_to_add]   

    def get_server_ip(self):
        _logger.info("Inside get_server_ip")
        openmrs_connect_configurations = self.env['insurance.config.settings'].get_values()
        _logger.info("Openmrs Configuration=%s", openmrs_connect_configurations)
        if not openmrs_connect_configurations:
            raise UserError("OpenMRS Configuration Not Set!!")
        return openmrs_connect_configurations['openmrs_base_url']

    def convert_url_to_pdf(self, url):
        _logger.info("Inside convert_url_to_pdf")
        # Use pdfkit to convert the URL content to a PDF
        pdf_content = pdfkit.from_url(url, False)

        # Create an attachment with the PDF content
        attachment = self.env['ir.attachment'].create({
            'name': 'patient-summary.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf'
        })
        # Return the attachment ID or any other result as needed
        return attachment.id

    def generate_opd_one_pager(self):
        _logger.info("Inside generate_opd_one_pager")
        ip_address = self.get_server_ip()
        _logger.info("Ip Address=%s", ip_address)
        for record in self:
            partner_uuid = record.partner_uuid
            external_visit_uuid = record.external_visit_uuid
            url = "{}:4433/onepager/?patient={}&visit={}".format(ip_address, partner_uuid, external_visit_uuid)
            _logger.info("URL=%s", url)
            attachment_id = record.convert_url_to_pdf(url)
            # Append the newly generated attachment ID to the existing ones
            record.attachment_ids = [(4, attachment_id)]

class InsuranceClaimLine(models.Model):
    _name = 'insurance.claim.line'
    _description = 'Insurance Claim Line Items'

    claim_id = fields.Many2one('insurance.claim', string="Claim Id", required=True, ondelete="cascade", index=True, copy=False)
    product_id = fields.Many2one('product.product', string="Product", domain=[('sale_ok', '=', True)], ondelete="Restrict", required=True)
    imis_product = fields.Many2one('insurance.odoo.product.map', string="Insurance Item", change_default=True)
    imis_product_code = fields.Char(string="IMIS Product Code", change_default=True)
    product_qty = fields.Integer(string="Qty", requred=True)
    price_unit = fields.Float(string="Unit Price")
    total = fields.Monetary(string="Total Price", currency_field="currency_id")
    currency_id = fields.Many2one(related='claim_id.currency_id', string="Currency", readonly=True, required=True)

class InsuranceClaimHistory(models.Model):
    _name = 'insurance.claim.history'
    _description = 'Insurance Claim History'

    claim_id = fields.Many2one('insurance.claim', string="Claim Id", required=True, ondelete="cascade", index=True, copy=False)
    partner_id = fields.Many2one(related="claim_id.partner_id", string="Insuree", readonly=True, index=True, tracking=True)
    claim_manager_id = fields.Many2one(related="claim_id.claim_manager_id", store=True, string="Claims Manager", readonly=True)
    claim_code = fields.Char(string="Claim Code")
    claim_status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('entered', 'Entered'),
        ('uploaded', 'Uploaded'),
        ('submitted', 'Submitted'),
        ('checked', 'Checked'),
        ('valuated', 'Valuated'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
        ('passed', 'Passed')
    ], string="Claim Status", default="draft")
    claim_comments = fields.Text(string="Claim Comments")
    rejection_reason = fields.Text(string="Rejection Reasons")

    @api.model
    def _add_claim_history(self, claim):
        _logger.info("Inside _add_claim_history")
        claim_history = {
            'claim_id': claim.id,
            'partner_id': claim.partner_id.id,
            'claim_manager_id': claim.claim_manager_id.id,
            'claim_code': claim.claim_code,
            'claim_status': claim.state,
            'claim_comments': claim.claim_comments,
            'rejection_reason': claim.rejection_reason
        }
        _logger.info(claim_history)
        return self.env['insurance.claim.history'].create(claim_history)



