"""
SubscriptIQ Product & Variant Configuration (Module 2)
Implements base products, product attributes, values, and dynamic variant pricing.
Example: Base Product Business Software (₹1,000) + Odoo Brand variant (+₹560) = ₹1,560.
"""

from ..services.odoo_adapter import Model, models, fields, api, ValidationError

class ProductAttribute(Model):
    _name = 'product.attribute'
    _description = 'Product Attribute'

    name = fields.Char(string="Attribute Name", required=True) # e.g. "Brand", "Edition"
    value_ids = fields.One2many('product.attribute.value', 'attribute_id', string="Values")

class ProductAttributeValue(Model):
    _name = 'product.attribute.value'
    _description = 'Product Attribute Value'

    name = fields.Char(string="Value Name", required=True) # e.g. "Default", "Odoo Brand"
    attribute_id = fields.Many2one('product.attribute', string="Attribute", required=True)
    price_extra = fields.Float(string="Additional Surcharge", default=0.0) # e.g. 560.0

class ProductTemplate(Model):
    _name = 'product.template'
    _description = 'Product Template'

    name = fields.Char(string="Product Name", required=True)
    product_type = fields.Selection([
        ('service', 'Service / Subscription'),
        ('consu', 'Consumable'),
        ('product', 'Storable Product')
    ], string="Product Type", default='service', required=True)
    list_price = fields.Float(string="Sales Price", required=True, default=1000.0)
    standard_price = fields.Float(string="Cost Price", default=400.0)
    description = fields.Text(string="Notes / Description")
    image_url = fields.Char(string="Product Image URL")
    active = fields.Boolean(string="Active", default=True)
    attribute_value_ids = fields.Many2many('product.attribute.value', string="Available Variants")
    is_subscription_product = fields.Boolean(string="Recurring Product", default=True)

class ProductProduct(Model):
    _name = 'product.product'
    _description = 'Product Variant'

    name = fields.Char(string="Variant Name", compute="_compute_display_name", store=True)
    product_tmpl_id = fields.Many2one('product.template', string="Base Template", required=True)
    attribute_value_ids = fields.Many2many('product.attribute.value', string="Selected Attributes")
    price_extra = fields.Float(string="Variant Surcharge", default=0.0)
    active = fields.Boolean(string="Active", default=True)

    @property
    def sales_price(self) -> float:
        """Calculates final variant price: base template price + attribute surcharges."""
        tmpl = self.product_tmpl_id
        if isinstance(tmpl, int) and hasattr(self, 'env'):
            tmpl = self.env['product.template'].browse(tmpl)
        base_price = getattr(tmpl, 'list_price', 0.0) if tmpl else 0.0
        if not base_price:
            base_price = getattr(self, 'list_price', 0.0) or 0.0
        extra = getattr(self, 'variant_extra_price', 0.0) or getattr(self, 'price_extra', 0.0) or 0.0
        if hasattr(self, 'attribute_value_ids') and self.attribute_value_ids:
            for val in self.attribute_value_ids:
                if isinstance(val, int) and hasattr(self, 'env'):
                    val = self.env['product.attribute.value'].browse(val)
                extra += getattr(val, 'price_extra', 0.0) or 0.0
        return float(base_price + extra)

    @property
    def computed_effective_price(self) -> float:
        return self.sales_price

    def _compute_display_name(self):
        for rec in self:
            tmpl = rec.product_tmpl_id
            if isinstance(tmpl, int) and hasattr(rec, 'env'):
                tmpl = rec.env['product.template'].browse(tmpl)
            tmpl_name = getattr(tmpl, 'name', 'Product')
            attrs = []
            if rec.attribute_value_ids:
                for v in rec.attribute_value_ids:
                    if isinstance(v, int) and hasattr(rec, 'env'):
                        v = rec.env['product.attribute.value'].browse(v)
                    v_name = getattr(v, 'name', str(v))
                    attrs.append(v_name)
            if attrs:
                rec.name = f"{tmpl_name} ({', '.join(attrs)})"
            else:
                rec.name = tmpl_name
