from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_sikili_ref = fields.Char(string='Référence Sikili')
