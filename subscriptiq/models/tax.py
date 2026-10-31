"""
SubscriptIQ Tax Configuration (Module 2)
Implements native Odoo accounting tax rules: percentage and fixed taxes,
tax-inclusive and tax-exclusive pricing calculations.
"""

from ..services.odoo_adapter import Model, models, fields, api, ValidationError

class AccountTax(Model):
    _name = 'account.tax'
    _description = 'Accounting Taxes'

    name = fields.Char(string="Tax Name", required=True) # e.g. "GST 18%", "VAT 5%"
    amount_type = fields.Selection([
        ('percent', 'Percentage (%)'),
        ('fixed', 'Fixed Amount')
    ], string="Tax Type", default='percent', required=True)
    amount = fields.Float(string="Tax Rate / Amount", required=True, default=18.0)
    price_include = fields.Boolean(string="Included in Price", default=False)
    active = fields.Boolean(string="Active", default=True)

    def compute_all(self, price_unit: float, quantity: float = 1.0) -> dict:
        """
        Computes base price, tax amount, and total price for a line item.
        Handles both tax-inclusive and tax-exclusive pricing.
        """
        qty = float(quantity)
        price = float(price_unit)
        total_price = price * qty

        if self.amount_type == 'percent':
            rate = self.amount / 100.0
            if self.price_include:
                # Tax is already inside price: base = total / (1 + rate)
                base = round(total_price / (1.0 + rate), 2)
                tax_amount = round(total_price - base, 2)
                total = total_price
            else:
                # Tax is added on top
                base = round(total_price, 2)
                tax_amount = round(base * rate, 2)
                total = round(base + tax_amount, 2)
        else: # fixed amount per unit
            fixed_tax = self.amount * qty
            if self.price_include:
                total = total_price
                tax_amount = round(fixed_tax, 2)
                base = round(total - tax_amount, 2)
            else:
                base = round(total_price, 2)
                tax_amount = round(fixed_tax, 2)
                total = round(base + tax_amount, 2)

        return {
            'total_excluded': base,
            'total_included': total,
            'tax_amount': tax_amount,
            'taxes': [{
                'id': self.id,
                'name': self.name,
                'amount': tax_amount,
                'rate': self.amount
            }]
        }
