"""
SubscriptIQ Discount Management (Module 2)
Implements fixed and percentage discount rules with minimum spend, minimum quantity,
validity dates, maximum usage caps, and product-specific vs entire-subscription scoping.
"""

import datetime
from decimal import Decimal
from ..services.odoo_adapter import Model, models, fields, api, ValidationError, UserError

class SubscriptiqDiscount(Model):
    _name = 'subscriptiq.discount'
    _description = 'Discount & Coupon Rules'

    name = fields.Char(string="Discount Name", required=True)
    code = fields.Char(string="Coupon / Rule Code", required=True)
    discount_type = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount')
    ], string="Type", default='percentage', required=True)
    value = fields.Float(string="Discount Value", required=True)
    scope = fields.Selection([
        ('entire_subscription', 'Entire Subscription'),
        ('specific_product', 'Specific Product Only')
    ], string="Application Scope", default='entire_subscription', required=True)
    product_id = fields.Many2one('product.template', string="Eligible Product")
    min_purchase_amount = fields.Float(string="Minimum Purchase Amount", default=0.0)
    min_quantity = fields.Integer(string="Minimum Product Quantity", default=1)
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    max_usage_limit = fields.Integer(string="Maximum Usage Limit", default=0) # 0 = unlimited
    usage_count = fields.Integer(string="Current Usage Count", default=0)
    active = fields.Boolean(string="Active", default=True)

    def validate_and_calculate(self, total_amount: float, quantity: int = 1, product_id: int = None, eval_date=None) -> float:
        """
        Validates discount eligibility against dates, usage caps, minimum spend, and scope.
        Returns the discount deduction amount, or raises ValidationError/UserError if invalid.
        """
        today = eval_date or datetime.date.today()
        if isinstance(today, str):
            today = datetime.datetime.strptime(today[:10], '%Y-%m-%d').date()

        if not self.active:
            raise ValidationError(f"Discount '{self.code}' is inactive.")

        # Check date range
        if self.start_date:
            sd = datetime.datetime.strptime(str(self.start_date)[:10], '%Y-%m-%d').date() if isinstance(self.start_date, str) else self.start_date
            if today < sd:
                raise ValidationError(f"Discount '{self.code}' is not yet valid (starts on {self.start_date}).")

        if self.end_date:
            ed = datetime.datetime.strptime(str(self.end_date)[:10], '%Y-%m-%d').date() if isinstance(self.end_date, str) else self.end_date
            if today > ed:
                raise ValidationError(f"Discount '{self.code}' has expired (ended on {self.end_date}).")

        # Check usage cap
        if self.max_usage_limit > 0 and self.usage_count >= self.max_usage_limit:
            raise ValidationError(f"Discount '{self.code}' has reached its maximum usage limit of {self.max_usage_limit}.")

        # Check minimum spend
        if self.min_purchase_amount > 0 and total_amount < self.min_purchase_amount:
            raise ValidationError(f"Minimum purchase amount of ₹{self.min_purchase_amount:,.2f} required for discount '{self.code}'.")

        # Check minimum quantity
        if self.min_quantity > 1 and quantity < self.min_quantity:
            raise ValidationError(f"Minimum quantity of {self.min_quantity} required for discount '{self.code}'.")

        # Check product scope
        if self.scope == 'specific_product' and self.product_id:
            target_pid = self.product_id.id if hasattr(self.product_id, 'id') else self.product_id
            if product_id != target_pid:
                raise ValidationError(f"Discount '{self.code}' is only applicable to product ID {target_pid}.")

        # Calculate discount amount
        if self.discount_type == 'percentage':
            deduction = (total_amount * self.value) / 100.0
        else:
            deduction = min(self.value, total_amount)

        return round(deduction, 2)

    def record_usage(self):
        """Increments usage counter atomically."""
        self.usage_count += 1
