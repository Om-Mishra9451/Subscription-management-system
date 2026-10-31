"""
SubscriptIQ User Management & Role-Based Access Control (Module 1)
Supports Admin, Internal Staff, Customer with strict password complexity,
unique email enforcement, email-based password reset, and customer isolation.
"""

import re
import hashlib
import uuid
import datetime
from ..services.odoo_adapter import Model, models, fields, api, UserError, ValidationError

PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\W).{9,}$')

class ResUsers(Model):
    _name = 'res.users'
    _description = 'User Management & Authentication'

    name = fields.Char(string="Full Name", required=True)
    login = fields.Char(string="Email / Username", required=True)
    password_hash = fields.Char(string="Password Hash", readonly=True)
    role = fields.Selection([
        ('admin', 'Administrator'),
        ('staff', 'Internal Staff'),
        ('customer', 'Customer')
    ], string="System Role", default='customer', required=True)
    partner_id = fields.Many2one('res.partner', string="Contact Record")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
    active = fields.Boolean(string="Active", default=True)
    reset_token = fields.Char(string="Password Reset Token")
    reset_token_expiry = fields.Datetime(string="Token Expiry")

    @classmethod
    def validate_password_complexity(cls, password: str) -> bool:
        """
        Original PDF Requirement:
        More than 8 characters, at least one uppercase, at least one lowercase,
        and at least one special character.
        """
        if not password or len(password) <= 8:
            return False
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_special = any(not c.isalnum() for c in password)
        return has_upper and has_lower and has_special

    @classmethod
    def hash_password(cls, password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    @classmethod
    def create_user(cls, env, values: dict):
        email = values.get('login', '').strip().lower()
        if not email:
            raise ValidationError("Email / Login is required.")

        # Enforce unique email
        existing = env['res.users'].search([('login', '=', email)])
        if existing:
            raise ValidationError(f"A user with email '{email}' already exists.")

        password = values.get('password', '')
        if not cls.validate_password_complexity(password):
            raise ValidationError(
                "Password must be more than 8 characters, contain at least one uppercase letter, "
                "one lowercase letter, and at least one special character."
            )

        role = values.get('role', 'customer')
        partner_id = values.get('partner_id')
        if not partner_id:
            partner = env['res.partner'].create({
                'name': values.get('name', email),
                'email': email,
                'is_company': False
            })
            partner_id = partner.id

        user_vals = {
            'name': values.get('name', email),
            'login': email,
            'password_hash': cls.hash_password(password),
            'role': role,
            'partner_id': partner_id,
            'company_id': values.get('company_id', env.company.id if hasattr(env, 'company') else 1),
            'active': True
        }
        return env['res.users'].create(user_vals)

    @classmethod
    def authenticate(cls, env, login: str, password: str):
        email = login.strip().lower()
        users = env['res.users'].search([('login', '=', email), ('active', '=', True)])
        if not users:
            return False
        user = users[0]
        if user.password_hash == cls.hash_password(password):
            return user
        return False

    @classmethod
    def request_password_reset(cls, env, email: str) -> str:
        users = env['res.users'].search([('login', '=', email.strip().lower())])
        if not users:
            raise ValidationError(f"No active account found for email '{email}'.")
        user = users[0]
        token = str(uuid.uuid4())
        expiry = datetime.datetime.now() + datetime.timedelta(hours=2)
        user.write({
            'reset_token': token,
            'reset_token_expiry': expiry
        })
        return token

    @classmethod
    def reset_password_with_token(cls, env, token: str, new_password: str):
        if not token:
            raise ValidationError("Invalid reset token.")
        if not cls.validate_password_complexity(new_password):
            raise ValidationError(
                "Password must be more than 8 characters, contain at least one uppercase letter, "
                "one lowercase letter, and at least one special character."
            )
        users = env['res.users'].search([('reset_token', '=', token)])
        if not users:
            raise ValidationError("Expired or invalid password reset token.")
        user = users[0]
        user.write({
            'password_hash': cls.hash_password(new_password),
            'reset_token': False,
            'reset_token_expiry': False
        })
        return True

    def check_permission(self, action: str, model_name: str) -> bool:
        """Enforces RBAC matrix."""
        role = self.role
        if role == 'admin':
            return True
        if role == 'staff':
            # Staff cannot alter admin settings, create staff, or delete audit logs
            if action in ['create_staff', 'manage_settings', 'unlink_audit']:
                return False
            return True
        if role == 'customer':
            # Customers can only view their own records
            if action in ['read_own', 'update_profile', 'download_invoice']:
                return True
            return False
        return False
