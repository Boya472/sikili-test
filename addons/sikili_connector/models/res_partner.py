from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_sikili_source = fields.Char(string='Source Sikili')
