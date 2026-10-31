"""
SubscriptIQ Product Management Extension
Extends product.template and product.product to support subscription variants,
extra variant pricing, and discount eligibility rules.
"""

from ..services.odoo_adapter import models, fields, api, ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_subscription_product = fields.Boolean(
        string="Recurring Subscription Product",
        default=False,
        help="Flags whether this product can be ordered as a recurring software subscription."
    )
    default_plan_id = fields.Many2one(
        'subscriptiq.plan',
        string="Default Subscription Plan",
        help="Default recurrence plan for this product."
    )
    eligible_for_discounts = fields.Boolean(
        string="Eligible for Promotional Discounts",
        default=True,
        help="Determines whether promotional discount codes can be applied to this product."
    )

class ProductProduct(models.Model):
    _inherit = 'product.product'

    variant_extra_price = fields.Float(
        string="Variant Surcharge / Extra Price",
        default=0.0,
        help="Additional price added to the base template sales price (e.g. +₹560 for branded tier)."
    )
    computed_effective_price = fields.Float(
        string="Final Calculated Sales Price",
        compute="_compute_effective_price",
        store=True,
        help="Template list price + variant extra price."
    )

    @api.depends('list_price', 'variant_extra_price')
    def _compute_effective_price(self):
        for prod in self:
            base = float(getattr(prod, 'list_price', 0.0) or 0.0)
            extra = float(getattr(prod, 'variant_extra_price', 0.0) or 0.0)
            prod.computed_effective_price = base + extra
