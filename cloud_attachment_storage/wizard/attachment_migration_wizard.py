# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CloudAttachmentMigrationWizard(models.TransientModel):
    _name = 'cloud.attachment.migration.wizard'
    _description = 'Batch Migrate Filestore Attachments to Cloud Storage'

    total_local_count = fields.Integer(
        string="Local Attachments Pending Migration",
        compute="_compute_migration_stats",
    )
    total_local_size_mb = fields.Float(
        string="Estimated Disk Space to Reclaim (MB)",
        compute="_compute_migration_stats",
        digits=(16, 2),
    )
    batch_size = fields.Integer(
        string="Batch Size",
        default=100,
        required=True,
        help="Number of attachments to process per execution to prevent timeout on large filestores.",
    )
    migrated_count = fields.Integer(string="Migrated So Far", default=0, readonly=True)
    state = fields.Selection([
        ('draft', 'Ready'),
        ('done', 'Completed'),
    ], default='draft')

    @api.depends('batch_size')
    def _compute_migration_stats(self):
        min_size_kb = int(self.env['ir.config_parameter'].sudo().get_param('cloud_attachment_storage.min_size_kb', 50))
        min_bytes = min_size_kb * 1024
        
        domain = [
            ('is_cloud_storage', '=', False),
            ('type', '=', 'binary'),
            ('store_fname', '!=', False),
            ('file_size', '>=', min_bytes),
        ]
        
        for record in self:
            attachments = self.env['ir.attachment'].search(domain)
            record.total_local_count = len(attachments)
            total_bytes = sum(attachments.mapped('file_size'))
            record.total_local_size_mb = total_bytes / (1024.0 * 1024.0)

    def action_migrate_batch(self):
        """Processes one batch of attachments and updates progress."""
        self.ensure_one()
        config = self.env['ir.config_parameter'].sudo()
        if config.get_param('cloud_attachment_storage.enabled', 'False') != 'True':
            raise UserError("Cloud Attachment Storage is currently disabled. Please enable and verify bucket settings first.")

        min_size_kb = int(config.get_param('cloud_attachment_storage.min_size_kb', 50))
        min_bytes = min_size_kb * 1024

        domain = [
            ('is_cloud_storage', '=', False),
            ('type', '=', 'binary'),
            ('store_fname', '!=', False),
            ('file_size', '>=', min_bytes),
        ]

        batch = self.env['ir.attachment'].search(domain, limit=self.batch_size)
        if not batch:
            self.state = 'done'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Migration Complete',
                    'message': 'All qualifying attachments have been successfully migrated to Cloud Storage!',
                    'type': 'success',
                    'sticky': True,
                }
            }

        # Process the batch
        batch._process_cloud_offload()
        processed_count = len(batch)
        self.migrated_count += processed_count

        # Check remaining
        remaining = self.env['ir.attachment'].search_count(domain)
        if remaining == 0:
            self.state = 'done'
            msg = f"Successfully migrated {self.migrated_count} attachments to Cloud Storage! All filestore attachments offloaded."
        else:
            msg = f"Migrated {processed_count} attachments. {remaining} remaining. Click 'Migrate Next Batch' to continue."

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cloud.attachment.migration.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'notification_msg': msg},
        }
