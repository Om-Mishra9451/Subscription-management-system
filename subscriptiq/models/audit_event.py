"""
SubscriptIQ Tamper-Evident Audit Event Model
Implements append-only financial and security event logging with cryptographic SHA-256 hash chaining.
Provides verifiable proof of who changed what, when, and the before/after values.
"""

import hashlib
import json
import datetime
from ..services.odoo_adapter import models, fields, api, AccessError

class SubscriptiqAuditEvent(models.Model):
    _name = 'subscriptiq.audit.event'
    _description = 'Cryptographic Audit Trail Event'
    _order = 'id desc'

    event_code = fields.Char(string="Event Code", required=True)
    actor_id = fields.Many2one('res.users', string="Actor / User", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1, required=True)

    target_model = fields.Char(string="Target Model", required=True)
    target_res_id = fields.Integer(string="Target Record ID", required=True)

    before_values = fields.Text(string="Before State (JSON)")
    after_values = fields.Text(string="After State (JSON)")

    timestamp = fields.Datetime(string="Event Timestamp", default=lambda self: fields.Datetime.now())
    correlation_id = fields.Char(string="Correlation / Request ID")

    # Cryptographic Hash Chaining
    previous_hash = fields.Char(string="Previous Event Hash (SHA-256)", readonly=True)
    event_hash = fields.Char(string="Current Event Hash (SHA-256)", readonly=True)

    @classmethod
    def record_event(cls, event_code, actor_id, company_id, target_model, target_res_id,
                     before_values=None, after_values=None, correlation_id=None, env=None):
        """
        Appends an immutable audit event to the ledger, computing cryptographic hash chaining.
        """
        table = cls._get_table(env)
        # Find the last record in this company
        last_event = None
        for eid in sorted(table.keys(), reverse=True):
            rec = table[eid]
            if getattr(rec, 'company_id', None) == company_id:
                last_event = rec
                break

        prev_hash = getattr(last_event, 'event_hash', '0000000000000000000000000000000000000000000000000000000000000000') if last_event else 'GENESIS_BLOCK_HASH_SUBSCRIPTIQ_AUDIT'

        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        before_str = json.dumps(before_values or {}, sort_keys=True)
        after_str = json.dumps(after_values or {}, sort_keys=True)

        # Compute SHA-256 event hash
        payload = f"{prev_hash}|{event_code}|{actor_id}|{company_id}|{target_model}|{target_res_id}|{before_str}|{after_str}|{ts}"
        curr_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()

        event_vals = {
            'event_code': event_code,
            'actor_id': actor_id if isinstance(actor_id, int) else (actor_id.id if hasattr(actor_id, 'id') else 1),
            'company_id': company_id if isinstance(company_id, int) else (company_id.id if hasattr(company_id, 'id') else 1),
            'target_model': target_model,
            'target_res_id': target_res_id,
            'before_values': before_str,
            'after_values': after_str,
            'timestamp': ts,
            'correlation_id': correlation_id or curr_hash[:16],
            'previous_hash': prev_hash,
            'event_hash': curr_hash
        }

        if env and 'subscriptiq.audit.event' in env.registry:
            return env['subscriptiq.audit.event'].create(event_vals)
        return cls.create_record(env, event_vals)

    def write(self, vals):
        """Strict append-only enforcement: mutations prohibited."""
        raise AccessError("Audit trail records are strictly tamper-evident and append-only. Modification is prohibited.")

    def unlink(self):
        """Strict append-only enforcement: deletion prohibited."""
        raise AccessError("Audit trail records are strictly tamper-evident and cannot be deleted.")
