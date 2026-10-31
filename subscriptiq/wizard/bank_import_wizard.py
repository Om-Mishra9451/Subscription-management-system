"""
SubscriptIQ Bank Statement Import Wizard
Enables user to upload CSV bank statement files, validates rows,
creates payment import batches, and generates candidate matches.
"""

import base64
from ..services.odoo_adapter import models, fields, api, UserError, ValidationError
from ..services.payment_matcher import PaymentMatcherEngine

class BankImportWizard(models.TransientModel):
    _name = 'subscriptiq.bank.import.wizard'
    _description = 'Bank Statement CSV Import Wizard'

    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company or 1, required=True)
    journal_id = fields.Many2one('account.journal', string="Target Bank Journal")
    csv_file = fields.Binary(string="Bank Statement CSV File", required=True)
    file_name = fields.Char(string="File Name")

    def action_process_csv(self):
        """Validates CSV and creates batch and lines."""
        self.ensure_one()
        if not self.csv_file:
            raise UserError("Please select a valid CSV file to upload.")

        file_bytes = base64.b64decode(self.csv_file)
        result = PaymentMatcherEngine.parse_and_validate_csv(file_bytes)

        if not result['accepted']:
            err_msg = "\n".join([f"Row {r['row']}: {r['reason']}" for r in result['rejected'][:5]])
            raise ValidationError(f"No valid transactions could be imported from CSV:\n{err_msg}")

        # Create batch
        batch = self.env['subscriptiq.payment.import'].create({
            'name': f"BATCH-{fields.Date.today()}-{self.file_name or 'bank_statement.csv'}",
            'company_id': self.company_id.id,
            'journal_id': self.journal_id.id if self.journal_id else False,
            'file_name': self.file_name,
            'transaction_count': len(result['accepted']),
            'total_amount': result['total_amount'],
            'state': 'processing'
        })

        # Create statement lines and match candidates
        line_model = self.env['subscriptiq.payment.import.line']
        cand_model = self.env['subscriptiq.match.candidate']

        for row in result['accepted']:
            line = line_model.create({
                'batch_id': batch.id,
                'company_id': self.company_id.id,
                'transaction_date': row['transaction_date'],
                'amount': row['amount'],
                'reference': row['reference'],
                'description': row['description'],
                'partner_name': row['partner_name'],
                'external_transaction_id': row['external_transaction_id'],
                'state': 'unmatched'
            })

            # Match candidates
            candidates = PaymentMatcherEngine.match_transaction(self.env, line, company_id=self.company_id.id)
            if candidates:
                for c in candidates:
                    cand_model.create({
                        'import_line_id': line.id,
                        'invoice_id': c['invoice_id'],
                        'confidence': c['confidence'],
                        'confidence_level': c['confidence_level'],
                        'explanation': c['reasons'],
                        'state': 'proposed'
                    })
                line.write({'state': 'matched'})

        batch.write({'state': 'completed'})

        return {
            'type': 'ir.actions.act_window',
            'name': f"Imported Statement Batch: {batch.name}",
            'res_model': 'subscriptiq.payment.import',
            'res_id': batch.id,
            'view_mode': 'form',
            'target': 'current'
        }
