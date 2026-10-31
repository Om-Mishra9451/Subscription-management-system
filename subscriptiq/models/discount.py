"""
SubscriptIQ Discount Management (Module 6)
Backwards-compatible export of SubscriptiqDiscount and SubscriptiqDiscountUsageHistory.
"""

from .discount_management import SubscriptiqDiscountRule, SubscriptiqDiscountUsageHistory

# Backwards compatible alias
SubscriptiqDiscount = SubscriptiqDiscountRule
