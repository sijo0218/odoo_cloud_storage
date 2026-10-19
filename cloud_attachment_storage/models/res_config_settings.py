# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
from .cloud_storage_client import CloudStorageClient


class ResConfigSettings(models.TransientModel):
    _inherit = 'res_config.settings'

    cloud_storage_enabled = fields.Boolean(
        string="Enable Cloud Attachment Storage",
        config_parameter='cloud_attachment_storage.enabled',
        default=False,
        help="When enabled, attachments exceeding the size threshold will be stored in S3/R2/MinIO.",
    )
    cloud_storage_provider = fields.Selection(
        selection=[
            ('r2', 'Cloudflare R2 (Recommended - Zero Egress Fees)'),
            ('s3', 'Amazon AWS S3'),
            ('minio', 'MinIO (Self-Hosted)'),
            ('wasabi', 'Wasabi Cloud Storage'),
            ('custom', 'Custom S3-Compatible Storage'),
        ],
        string="Storage Provider",
        config_parameter='cloud_attachment_storage.provider',
        default='r2',
    )
    cloud_storage_endpoint = fields.Char(
        string="Endpoint URL",
        config_parameter='cloud_attachment_storage.endpoint',
        help="Endpoint URL (e.g., https://<account_id>.r2.cloudflarestorage.com or https://minio.yourdomain.com:9000). Leave blank for default AWS S3.",
    )
    cloud_storage_bucket = fields.Char(
        string="Bucket Name",
        config_parameter='cloud_attachment_storage.bucket',
        help="Target bucket name where files will be stored.",
    )
    cloud_storage_access_key = fields.Char(
        string="Access Key ID",
        config_parameter='cloud_attachment_storage.access_key',
    )
    cloud_storage_secret_key = fields.Char(
        string="Secret Access Key",
        config_parameter='cloud_attachment_storage.secret_key',
    )
    cloud_storage_region = fields.Char(
        string="Region",
        config_parameter='cloud_attachment_storage.region',
        default='auto',
        help="Bucket region (e.g., us-east-1, eu-west-1, or 'auto' for Cloudflare R2).",
    )
    cloud_storage_min_size_kb = fields.Integer(
        string="Minimum File Size Threshold (KB)",
        config_parameter='cloud_attachment_storage.min_size_kb',
        default=50,
        help="Files smaller than this threshold remain in local filestore to optimize latency for small icons/avatars.",
    )
    cloud_storage_delete_local = fields.Boolean(
        string="Delete Local Filestore Copy",
        config_parameter='cloud_attachment_storage.delete_local',
        default=True,
        help="If checked, local file copies are removed after successful upload to save 100% of server disk space.",
    )
    cloud_storage_use_presigned_urls = fields.Boolean(
        string="Use Direct Pre-Signed Download URLs",
        config_parameter='cloud_attachment_storage.use_presigned_urls',
        default=True,
        help="Generates temporary direct pre-signed URLs for downloads, reducing Odoo server bandwidth and worker load.",
    )

    def action_test_cloud_connection(self):
        """Tests bucket connectivity and read/write privileges."""
        self.ensure_one()
        endpoint = self.cloud_storage_endpoint
        access_key = self.cloud_storage_access_key
        secret_key = self.cloud_storage_secret_key
        bucket = self.cloud_storage_bucket
        region = self.cloud_storage_region or 'auto'

        if not bucket or not access_key or not secret_key:
            raise UserError("Please fill in Bucket Name, Access Key, and Secret Access Key before testing connection.")

        success, message = CloudStorageClient.test_bucket_connection(
            endpoint_url=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            bucket_name=bucket,
            region_name=region if region != 'auto' else None,
        )

        if not success:
            raise UserError(f"Cloud Storage Connection Failed!\n\n{message}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Connection Verified',
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_migration_wizard(self):
        """Opens the 1-click batch migration wizard."""
        return {
            'name': 'Migrate Filestore Attachments to Cloud',
            'type': 'ir.actions.act_window',
            'res_model': 'cloud.attachment.migration.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
