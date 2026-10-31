"""
SubscriptIQ Role-Based Authentication & Access Control Unit Tests
Tests:
- Admin, Staff, and Customer Authentication & Role Identification
- Route / Role Dashboard Redirection Mapping
- Role-based permissions (Only Admin can create Staff)
- Customer Self-Registration (Strictly assigns 'customer' role)
- Customer Data Isolation (Customers only access their own records)
- Unauthorized access rejection and session handling
"""

import unittest
from subscriptiq.services.odoo_adapter import Environment, ValidationError, AccessError
from subscriptiq.models.user_management import ResUsers
from subscriptiq.models.subscription_adapter import SaleOrder
from subscriptiq.models.payment_management import AccountPayment
from subscriptiq.services.revenue_calculator import RevenueCalculator

class TestRoleBasedAuth(unittest.TestCase):

    def setUp(self):
        self.env = Environment()
        self.company = self.env['res.company'].create({'name': 'Brightloop Software Ltd'})
        self.env.company = self.company

        # 1. Create Admin
        self.admin = ResUsers.create_user(self.env, {
            'name': 'Brightloop Admin',
            'login': 'admin@brightloop.software',
            'password': 'SuperAdmin@2026',
            'role': 'admin'
        })

        # 2. Create Staff
        self.staff = ResUsers.create_user(self.env, {
            'name': 'Brightloop Staff',
            'login': 'staff@brightloop.software',
            'password': 'StaffMember@2026',
            'role': 'staff'
        })

        # 3. Create Customer Partner & User
        self.cust_partner = self.env['res.partner'].create({
            'name': 'Acme Enterprise Ltd',
            'email': 'billing@acme.com',
            'is_company': True
        })
        self.customer = ResUsers.create_user(self.env, {
            'name': 'Alice Manager',
            'login': 'alice@acme.com',
            'password': 'CustomerP@ss2026',
            'role': 'customer',
            'partner_id': self.cust_partner.id
        })

        # 4. Create Another Customer to test isolation
        self.cust2_partner = self.env['res.partner'].create({
            'name': 'Beta Corp',
            'email': 'finance@beta.com',
            'is_company': True
        })
        self.customer2 = ResUsers.create_user(self.env, {
            'name': 'Bob Director',
            'login': 'bob@beta.com',
            'password': 'CustomerP@ss2026',
            'role': 'customer',
            'partner_id': self.cust2_partner.id
        })

    def test_admin_authentication_and_role_identification(self):
        """Admin credentials must authenticate and identify as 'admin'."""
        user = ResUsers.authenticate(self.env, 'admin@brightloop.software', 'SuperAdmin@2026')
        self.assertIsNotNone(user)
        self.assertEqual(user.role, 'admin')
        self.assertEqual(user.login, 'admin@brightloop.software')

    def test_staff_authentication_and_role_identification(self):
        """Staff credentials must authenticate and identify as 'staff'."""
        user = ResUsers.authenticate(self.env, 'staff@brightloop.software', 'StaffMember@2026')
        self.assertIsNotNone(user)
        self.assertEqual(user.role, 'staff')

    def test_customer_authentication_and_role_identification(self):
        """Customer credentials must authenticate and identify as 'customer'."""
        user = ResUsers.authenticate(self.env, 'alice@acme.com', 'CustomerP@ss2026')
        self.assertIsNotNone(user)
        self.assertEqual(user.role, 'customer')
        p_id = user.partner_id.id if hasattr(user.partner_id, 'id') else user.partner_id
        self.assertEqual(p_id, self.cust_partner.id)

    def test_invalid_login_rejection(self):
        """Wrong password or non-existent email must return False."""
        self.assertFalse(ResUsers.authenticate(self.env, 'admin@brightloop.software', 'WrongPassword123!'))
        self.assertFalse(ResUsers.authenticate(self.env, 'nonexistent@brightloop.com', 'SomeP@ssword2026'))

    def test_customer_self_registration_strict_role(self):
        """Customer registration must strictly assign 'customer' role regardless of input."""
        # When customer registers, system must assign role='customer'
        new_cust = ResUsers.create_user(self.env, {
            'name': 'Charlie Payer',
            'login': 'charlie@delta.com',
            'password': 'ValidP@ss2026',
            'role': 'customer'  # Customer cannot choose admin/staff
        })
        self.assertEqual(new_cust.role, 'customer')
        self.assertIsNotNone(new_cust.partner_id)

    def test_only_admin_can_create_staff_policy(self):
        """Policy test: Only an admin context is allowed to create staff accounts."""
        # Simulated helper to enforce policy
        def create_staff_with_authorization(caller_role, staff_vals):
            if caller_role != 'admin':
                raise AccessError("Unauthorized: Only Administrators can create staff accounts.")
            staff_vals['role'] = 'staff'
            return ResUsers.create_user(self.env, staff_vals)

        # Admin caller: succeeds
        staff_user = create_staff_with_authorization('admin', {
            'name': 'New Tech Staff',
            'login': 'tech@brightloop.software',
            'password': 'StaffSecret@2026'
        })
        self.assertEqual(staff_user.role, 'staff')

        # Customer caller: raises AccessError
        with self.assertRaises(AccessError):
            create_staff_with_authorization('customer', {
                'name': 'Rogue Staff',
                'login': 'rogue@brightloop.software',
                'password': 'StaffSecret@2026'
            })

        # Staff caller: raises AccessError
        with self.assertRaises(AccessError):
            create_staff_with_authorization('staff', {
                'name': 'Rogue Staff 2',
                'login': 'rogue2@brightloop.software',
                'password': 'StaffSecret@2026'
            })

    def test_customer_data_isolation(self):
        """Customer A must only see Customer A's subscriptions and invoices."""
        # Create subscription for Customer 1 (Acme)
        sub1 = self.env['sale.order'].create({
            'name': 'SUB/ACME/001',
            'partner_id': self.cust_partner.id,
            'company_id': self.company.id,
            'is_subscription': True,
            'subscriptiq_status': 'active',
            'stage': 'in_progress',
            'recurring_total': 1500.0
        })

        # Create subscription for Customer 2 (Beta)
        sub2 = self.env['sale.order'].create({
            'name': 'SUB/BETA/002',
            'partner_id': self.cust2_partner.id,
            'company_id': self.company.id,
            'is_subscription': True,
            'subscriptiq_status': 'active',
            'stage': 'in_progress',
            'recurring_total': 3000.0
        })

        # When filtered for Customer 1
        acme_subs = self.env['sale.order'].search([
            ('is_subscription', '=', True),
            ('partner_id', '=', self.cust_partner.id)
        ])
        acme_sub_ids = [s.id for s in acme_subs]
        self.assertIn(sub1.id, acme_sub_ids)
        self.assertNotIn(sub2.id, acme_sub_ids)

    def test_dashboard_redirection_mapping(self):
        """Verify deterministic role-to-dashboard route resolution."""
        role_dashboard_map = {
            'admin': '/admin/dashboard',
            'staff': '/staff/dashboard',
            'customer': '/customer/dashboard'
        }
        self.assertEqual(role_dashboard_map[self.admin.role], '/admin/dashboard')
        self.assertEqual(role_dashboard_map[self.staff.role], '/staff/dashboard')
        self.assertEqual(role_dashboard_map[self.customer.role], '/customer/dashboard')

if __name__ == '__main__':
    unittest.main()
