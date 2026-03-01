from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)

class InsuranceConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'insurance.config.settings'
    _descripton = 'Insurance Config Settings'

    username = fields.Char(string="Username", required=True)
    password = fields.Char(string="Password", required=True)
    base_url = fields.Char(string="Base Url")
    openmrs_username = fields.Char(string="User Name")
    openmrs_password = fields.Char(string="Password")
    openmrs_base_url = fields.Char(string="Base Url")
    insurance_journal = fields.Char(string="Insurance Journal")
    manually_setup_claim_code = fields.Boolean(string="Use default claim code", help="Use default claim code or set it up manually")
    claim_code_start_range = fields.Integer(string="Start Range", help="start value for claim code")
    claim_code_end_range = fields.Integer(string="End Range", help="End value for claim code")
    claim_code_next_val = fields.Integer(string="Next Value")

    @api.model
    def get_values(self):
        res = super().get_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        res.update(
            username = param_obj.get_param('insurance.config.settings.username', default=''),
            password = param_obj.get_param('insurance.config.settings.password', default=''),
            base_url = param_obj.get_param('insurance.config.settings.base_url', default=''),
            insurance_journal = param_obj.get_param('insurance.config.settings.insurance_journal', default=''),
            manually_setup_claim_code = param_obj.get_param('insurance.config.settings.manually_setup_claim_code', default=''),
            claim_code_start_range = param_obj.get_param('insurance.config.settings.claim_code_start_range', default=''),
            claim_code_end_range = param_obj.get_param('insurance.config.settings.claim_code_end_range', default=''),
            claim_code_next_val = param_obj.get_param('insurance.config.settings.claim_code_next_val', default='')
        )
        return res
    
    def set_values(self):
        super().set_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        param_obj.set_param('insurance.config.settings.username', self.username)
        param_obj.set_param('insurance.config.settings.password', self.password)
        param_obj.set_param('insurance.config.settings.base_url', self.base_url)
        param_obj.set_param('insurance.config.settings.insurance_journal', self.insurance_journal)
        param_obj.set_param('insurance.config.settings.manually_setup_claim_code', self.manually_setup_claim_code)
        param_obj.set_param('insurance.config.settings.claim_code_start_range', self.claim_code_start_range)
        param_obj.set_param('insurance.config.settings.claim_code_end_range', self.claim_code_end_range)
        param_obj.set_param('insurance.config.settings.claim_code_next_val', self.claim_code_next_val)

    def action_test_connection(self):
        _logger.info("Action Test Connection")
        for rec in self:
            username = rec.username
            password = rec.password
            base_url = rec.base_url

            _logger.info("Username:%s", username)
            _logger.info("Password:%s", password)
            _logger.info("Base Url:%s", base_url)

            response = rec.env['insurance.connect'].authenticate(username, password, base_url)
            _logger.info("Response:%s", response)
            if response:
                raise UserError(response)
            else:
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "insurance.config.settings",
                    "views": [(False, "form")],
                    "res_id": rec.id,
                    "target": "main",
                    "context": {"show_message": True}
                } 
    
    def get_next_value(self):
        _logger.info("Inside get_next_value")
        param_obj = self.env['ir.config_parameter'].sudo()

        next_value = param_obj.get_param('insurance.config.settings.claim_code_next_val')
        _logger.info("Next Value = %s", next_value)

        next_value = int(next_value)

        next_value += 1

        param_obj.set_param('insurance.config.settings.claim_code_next_val', next_value)
        _logger.info("After update, next value = %s", next_value)

        return next_value


    
   
