"""
SubscriptIQ Quotation Templates (Module 3)
Allows sales teams to configure reusable quotation templates with preset
products, plans, quantities, unit prices, taxes, and validity periods.
"""

from ..services.odoo_adapter import Model, models, fields, api

class SaleOrderTemplate(Model):
    _name = 'sale.order.template'
    _description = 'Quotation Template'

    name = fields.Char(string="Template Name", required=True)
    plan_id = fields.Many2one('subscriptiq.plan', string="Default Plan")
    number_of_days = fields.Integer(string="Quotation Validity (Days)", default=30)
    note = fields.Text(string="Default Terms & Conditions")
    line_ids = fields.One2many('sale.order.template.line', 'template_id', string="Lines")
    active = fields.Boolean(string="Active", default=True)

class SaleOrderTemplateLine(Model):
    _name = 'sale.order.template.line'
    _description = 'Quotation Template Line'

    template_id = fields.Many2one('sale.order.template', string="Template", required=True)
    product_id = fields.Many2one('product.template', string="Product", required=True)
    product_uom_qty = fields.Float(string="Quantity", default=1.0)
    price_unit = fields.Float(string="Unit Price", default=0.0)
    discount = fields.Float(string="Default Discount (%)", default=0.0)
