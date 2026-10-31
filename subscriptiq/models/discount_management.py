"""
SubscriptIQ Discount Management Module (Module 6)
Implements comprehensive promotional and rule-based discount management:
- Fixed Amount and Percentage discounts
- Minimum purchase amount and minimum product quantity constraints
- Start and expiry date validation
- Maximum usage limits with transactional atomic counters
- Product-specific, plan-specific, and entire-subscription applicability
- Traceable usage history ledger linked to subscriptions and invoices
- Admin-only policy creation and modification
"""

import datetime
from decimal import Decimal
from ..services.odoo_adapter import Model, models, fields, api, ValidationError, UserError

class SubscriptiqDiscountUsageHistory(Model):
    _name = 'subscriptiq.discount.usage.history'
    _description = 'Discount Usage Audit Ledger'

    name = fields.Char(string="Reference", required=True)
    discount_id = fields.Many2one('subscriptiq.discount', string="Discount Rule", required=True)
    invoice_id = fields.Many2one('account.move', string="Generated Invoice")
    subscription_id = fields.Many2one('sale.order', string="Subscription Order")
    partner_id = fields.Many2one('res.partner', string="Customer")
    original_amount = fields.Float(string="Amount Before Discount", default=0.0)
    discount_amount = fields.Float(string="Discount Deduction", default=0.0)
    final_amount = fields.Float(string="Net Amount Billed", default=0.0)
    usage_date = fields.Date(string="Usage Date", default=lambda self: datetime.date.today())
    user_id = fields.Many2one('res.users', string="Applied By User")


class SubscriptiqDiscountRule(Model):
    _name = 'subscriptiq.discount'
    _description = 'Subscription Promotional Discount Rule'

    name = fields.Char(string="Discount Name", required=True)
    code = fields.Char(string="Coupon / Rule Code", required=True)
    discount_type = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount (₹)')
    ], string="Discount Type", default='percentage', required=True)
    value = fields.Float(string="Discount Value", required=True)
    
    # Scoping
    apply_to_entire_subscription = fields.Boolean(string="Apply to Entire Subscription", default=True)
    scope = fields.Selection([
        ('entire_subscription', 'Entire Subscription'),
        ('specific_product', 'Specific Product Only'),
        ('specific_plan', 'Specific Plan Only')
    ], string="Application Scope", default='entire_subscription', required=True)
    
    product_id = fields.Many2one('product.template', string="Eligible Product")
    applicable_product_ids = fields.Many2many('product.template', string="Applicable Products")
    applicable_plan_ids = fields.Many2many('subscriptiq.plan', string="Applicable Subscription Plans")
    
    # Constraints
    min_purchase_amount = fields.Float(string="Minimum Purchase Amount", default=0.0)
    min_quantity = fields.Integer(string="Minimum Product Quantity", default=1)
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="Expiry Date")
    max_usage_limit = fields.Integer(string="Maximum Usage Limit (0=Unlimited)", default=0)
    usage_count = fields.Integer(string="Current Usage Count", default=0)
    active = fields.Boolean(string="Active Status", default=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)

    @api.constrains('value', 'discount_type')
    def _check_discount_value(self):
        for rec in self:
            if rec.value < 0:
                raise ValidationError("Discount value cannot be negative.")
            if rec.discount_type == 'percentage' and rec.value > 100.0:
                raise ValidationError(f"Percentage discount cannot exceed 100% (got {rec.value}%).")

    @api.constrains('start_date', 'end_date')
    def _check_date_validity(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                sd = datetime.datetime.strptime(str(rec.start_date)[:10], '%Y-%m-%d').date() if isinstance(rec.start_date, str) else rec.start_date
                ed = datetime.datetime.strptime(str(rec.end_date)[:10], '%Y-%m-%d').date() if isinstance(rec.end_date, str) else rec.end_date
                if ed < sd:
                    raise ValidationError(f"Discount end date ({rec.end_date}) cannot be prior to start date ({rec.start_date}).")

    @classmethod
    def create_record(cls, env, vals):
        val = float(vals.get('value', 0.0))
        dtype = vals.get('discount_type', 'percentage')
        if val < 0:
            raise ValidationError("Discount value cannot be negative.")
        if dtype == 'percentage' and val > 100.0:
            raise ValidationError(f"Percentage discount cannot exceed 100% (got {val}%).")
        sd = vals.get('start_date')
        ed = vals.get('end_date')
        if sd and ed:
            sd_d = datetime.datetime.strptime(str(sd)[:10], '%Y-%m-%d').date() if isinstance(sd, str) else sd
            ed_d = datetime.datetime.strptime(str(ed)[:10], '%Y-%m-%d').date() if isinstance(ed, str) else ed
            if ed_d < sd_d:
                raise ValidationError(f"Discount end date ({ed}) cannot be prior to start date ({sd}).")
        return super().create_record(env, vals)

    @classmethod
    def check_admin_permission(cls, user):
        """Enforces that only Admin persona can create or modify discounts."""
        if hasattr(user, 'has_role') and not user.has_role('admin'):
            raise UserError("Access Denied: Only administrators can create or modify discount rules.")

    def validate_and_calculate(self, total_amount: float, quantity: int = 1, product_id: int = None, plan_id: int = None, eval_date=None) -> float:
        """
        Validates discount eligibility against dates, usage caps, minimum spend, quantity, and product/plan scope.
        Returns the discount deduction amount, or raises ValidationError/UserError if invalid.
        """
        today = eval_date or datetime.date.today()
        if isinstance(today, str):
            today = datetime.datetime.strptime(today[:10], '%Y-%m-%d').date()

        if not self.active:
            raise ValidationError(f"Discount rule '{self.code}' is inactive.")

        # Check date validity
        if self.start_date:
            sd = datetime.datetime.strptime(str(self.start_date)[:10], '%Y-%m-%d').date() if isinstance(self.start_date, str) else self.start_date
            if today < sd:
                raise ValidationError(f"Discount '{self.code}' is not yet valid (starts on {self.start_date}).")

        if self.end_date:
            ed = datetime.datetime.strptime(str(self.end_date)[:10], '%Y-%m-%d').date() if isinstance(self.end_date, str) else self.end_date
            if today > ed:
                raise ValidationError(f"Discount '{self.code}' has expired on {self.end_date}.")

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
        if self.scope == 'specific_product' or not self.apply_to_entire_subscription:
            if self.product_id:
                target_pid = self.product_id.id if hasattr(self.product_id, 'id') else self.product_id
                if product_id and product_id != target_pid:
                    raise ValidationError(f"Discount '{self.code}' is only applicable to product ID {target_pid}.")
            elif hasattr(self, 'applicable_product_ids') and self.applicable_product_ids:
                pids = [p.id if hasattr(p, 'id') else p for p in self.applicable_product_ids]
                if product_id and product_id not in pids:
                    raise ValidationError(f"Discount '{self.code}' is not applicable to product ID {product_id}.")

        # Check plan scope
        if self.scope == 'specific_plan' and hasattr(self, 'applicable_plan_ids') and self.applicable_plan_ids:
            plan_ids = [p.id if hasattr(p, 'id') else p for p in self.applicable_plan_ids]
            if plan_id and plan_id not in plan_ids:
                raise ValidationError(f"Discount '{self.code}' is not applicable to plan ID {plan_id}.")

        # Calculate discount deduction
        if self.discount_type == 'percentage':
            deduction = (total_amount * self.value) / 100.0
        else:
            deduction = min(self.value, total_amount)

        return round(deduction, 2)

    def record_usage(self, invoice=None, subscription=None, partner=None, original_amount=0.0, deduction=0.0, final_amount=0.0):
        """
        Increments usage counter transactionally and records audit history ledger entry.
        """
        if self.max_usage_limit > 0 and self.usage_count >= self.max_usage_limit:
            raise ValidationError(f"Usage limit exhausted for discount '{self.code}'.")

        self.usage_count += 1
        
        env = getattr(self, 'env', None)
        if env and 'subscriptiq.discount.usage.history' in env:
            ref_seq = f"DU/{datetime.date.today().strftime('%Y%m')}/{env['subscriptiq.discount.usage.history'].search_count([]) + 1:04d}"
            env['subscriptiq.discount.usage.history'].create({
                'name': ref_seq,
                'discount_id': self.id,
                'invoice_id': invoice.id if hasattr(invoice, 'id') else invoice,
                'subscription_id': subscription.id if hasattr(subscription, 'id') else subscription,
                'partner_id': partner.id if hasattr(partner, 'id') else partner,
                'original_amount': original_amount,
                'discount_amount': deduction,
                'final_amount': final_amount,
                'usage_date': str(datetime.date.today()),
                'user_id': env.user.id if hasattr(env, 'user') and env.user else 1
            })
