"""
SubscriptIQ Plan and Discount Management Models
Defines recurring subscription plans with supported intervals (daily, weekly, monthly, yearly),
policies for pause, renewal, closure, and administrator-managed discount rules.
"""

import datetime
from ..services.odoo_adapter import models, fields, api, ValidationError

class SubscriptiqPlan(models.Model):
    _name = 'subscriptiq.plan'
    _description = 'Subscription Plan Definition'

    name = fields.Char(string="Plan Name", required=True)
    code = fields.Char(string="Plan Code", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1)
    price = fields.Float(string="Base Recurring Price", required=True, default=0.0)
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.ref('base.INR', raise_if_not_found=False) or 1)

    billing_interval = fields.Selection([
        ('daily', 'Daily (Custom Recurrence Extension)'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ], string="Billing Interval", required=True, default='monthly')

    billing_interval_count = fields.Integer(string="Interval Count", default=1, required=True)
    min_quantity = fields.Float(string="Minimum Quantity", default=1.0)

    availability_start_date = fields.Date(string="Availability Start Date")
    availability_end_date = fields.Date(string="Availability End Date")

    # Policies
    auto_close_policy = fields.Selection([
        ('immediate', 'Close Immediately on Expiry'),
        ('grace_period', 'Allow Grace Period Before Close'),
        ('manual', 'Manual Review Required')
    ], string="Automatic Closing Policy", default='grace_period')
    grace_period_days = fields.Integer(string="Grace Period Days", default=7)

    early_closure_policy = fields.Selection([
        ('allowed_no_penalty', 'Allowed Without Penalty'),
        ('allowed_prorated', 'Allowed with Prorated Adjustment'),
        ('disallowed', 'Strict Term (No Early Cancellation)')
    ], string="Early Closure Policy", default='allowed_prorated')

    pause_policy = fields.Selection([
        ('allowed', 'Allowed (Suspends Billing)'),
        ('disallowed', 'Not Permitted')
    ], string="Pause Policy", default='allowed')
    max_pause_days = fields.Integer(string="Maximum Pause Duration (Days)", default=60)

    renewal_policy = fields.Selection([
        ('auto_renew', 'Automatic Renewal at Period End'),
        ('manual_quote', 'Generate Renewal Quotation for Approval'),
        ('terminate', 'Terminate at Term End')
    ], string="Renewal Policy", default='auto_renew')

    active = fields.Boolean(string="Active", default=True)

    @api.constrains('availability_start_date', 'availability_end_date')
    def _check_availability_dates(self):
        for plan in self:
            if plan.availability_start_date and plan.availability_end_date:
                if plan.availability_start_date > plan.availability_end_date:
                    raise ValidationError("Availability start date cannot be later than availability end date.")

    @api.constrains('min_quantity')
    def _check_min_quantity(self):
        for plan in self:
            if plan.min_quantity <= 0:
                raise ValidationError("Minimum quantity must be greater than zero.")

class SubscriptiqDiscountRule(models.Model):
    _name = 'subscriptiq.discount.rule'
    _description = 'Subscription Discount Rule'

    name = fields.Char(string="Discount Name", required=True)
    code = fields.Char(string="Promo / Discount Code", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1)

    discount_type = fields.Selection([
        ('percentage', 'Percentage Discount (%)'),
        ('fixed', 'Fixed Monetary Amount (₹)')
    ], string="Discount Type", required=True, default='percentage')
    discount_value = fields.Float(string="Discount Value", required=True, default=0.0)

    scope = fields.Selection([
        ('subscription_wide', 'Subscription-Wide'),
        ('product_specific', 'Product-Specific')
    ], string="Discount Scope", default='subscription_wide')
    applicable_product_ids = fields.Many2many('product.product', string="Applicable Products")

    min_purchase_amount = fields.Float(string="Minimum Purchase Amount", default=0.0)
    min_quantity = fields.Float(string="Minimum Quantity", default=1.0)

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    max_usage_limit = fields.Integer(string="Maximum Usage Limit (Lifetime)", default=0, help="0 means unlimited.")
    usage_count = fields.Integer(string="Current Usage Count", default=0, readonly=True)

    active = fields.Boolean(string="Active", default=True)

    @api.constrains('discount_value', 'discount_type')
    def _check_discount_value(self):
        for rule in self:
            if rule.discount_value <= 0:
                raise ValidationError("Discount value must be greater than zero.")
            if rule.discount_type == 'percentage' and rule.discount_value > 100.0:
                raise ValidationError("Percentage discount cannot exceed 100%.")

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rule in self:
            if rule.start_date and rule.end_date and rule.start_date > rule.end_date:
                raise ValidationError("Discount start date cannot be later than end date.")
