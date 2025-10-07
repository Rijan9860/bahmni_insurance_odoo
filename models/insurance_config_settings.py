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
    insurance_journal = fields.Char(string="Insurance Journal", required=True)
    
    @api.model
    def get_values(self):
        res = super().get_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        res.update(
            username = param_obj.get_param('insurance.config.settings.username', default=''),
            password = param_obj.get_param('insurance.config.settings.password', default=''),
        )
        return res
    
    @api.model
    def get_insurance_journal(self):
        res = super().get_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        res.update(
            insurance_journal = param_obj.get_param('insurance.config.settings.insurance_journal', default=''),
        )

    def set_values(self):
        super().set_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        param_obj.set_param('insurance.config.settings.username', self.username)
        param_obj.set_param('insurance.config.settings.password', self.password)
        param_obj.set_param('insurance.config.settings.insurance_journal', self.insurance_journal)


    
   
