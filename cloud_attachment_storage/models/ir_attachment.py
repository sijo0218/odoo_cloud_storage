# -*- coding: utf-8 -*-
import io
import os
import logging
from odoo import api, fields, models
from .cloud_storage_client import CloudStorageClient, get_config_param

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    is_cloud_storage = fields.Boolean(
        string="Stored in Cloud",
        default=False,
        index=True,
        readonly=True,
        help="Indicates whether this attachment binary is hosted in Cloud Storage (S3 / R2 / MinIO).",
    )
    cloud_storage_key = fields.Char(
        string="Cloud Object Key",
        index=True,
        readonly=True,
        help="S3 / R2 Object Key in the target bucket.",
    )
    cloud_storage_provider = fields.Char(
        string="Cloud Provider",
        readonly=True,
    )
    cloud_storage_presigned_url = fields.Char(
        string="Direct Download URL",
        compute="_compute_cloud_presigned_url",
        help="Temporary secure pre-signed download link directly from the cloud provider.",
    )

    def _compute_cloud_presigned_url(self):
        enabled = get_config_param(self.env, 'cloud_attachment_storage.enabled', False, 'bool')
        bucket = get_config_param(self.env, 'cloud_attachment_storage.bucket')
        endpoint = get_config_param(self.env, 'cloud_attachment_storage.endpoint')
        access_key = get_config_param(self.env, 'cloud_attachment_storage.access_key')
        secret_key = get_config_param(self.env, 'cloud_attachment_storage.secret_key')
        region = get_config_param(self.env, 'cloud_attachment_storage.region', 'auto')

        client = None
        if enabled and bucket and access_key and secret_key:
            try:
                client = CloudStorageClient.get_client(
                    endpoint_url=endpoint,
                    access_key=access_key,
                    secret_key=secret_key,
                    region_name=region if region != 'auto' else None,
                )
            except Exception as e:
                _logger.warning("Failed to initialize cloud client for presigned URL: %s", e)

        for record in self:
            if record.is_cloud_storage and record.cloud_storage_key and client:
                try:
                    record.cloud_storage_presigned_url = CloudStorageClient.generate_presigned_url(
                        client=client,
                        bucket_name=bucket,
                        key=record.cloud_storage_key,
                        expiration=3600,
                    )
                except Exception:
                    record.cloud_storage_presigned_url = False
            else:
                record.cloud_storage_presigned_url = False

    def _file_read(self):
        """Overrides filestore read to transparently pull from Cloud Storage when flagged."""
        self.ensure_one()
        if self.is_cloud_storage and self.cloud_storage_key:
            try:
                bucket = get_config_param(self.env, 'cloud_attachment_storage.bucket')
                endpoint = get_config_param(self.env, 'cloud_attachment_storage.endpoint')
                access_key = get_config_param(self.env, 'cloud_attachment_storage.access_key')
                secret_key = get_config_param(self.env, 'cloud_attachment_storage.secret_key')
                region = get_config_param(self.env, 'cloud_attachment_storage.region', 'auto')

                client = CloudStorageClient.get_client(
                    endpoint_url=endpoint,
                    access_key=access_key,
                    secret_key=secret_key,
                    region_name=region if region != 'auto' else None,
                )
                data = CloudStorageClient.download_object(client, bucket, self.cloud_storage_key)
                return data
            except Exception as e:
                _logger.error("Failed to read cloud storage attachment ID %s (key %s): %s", self.id, self.cloud_storage_key, e)
                return super()._file_read()
        return super()._file_read()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._process_cloud_offload()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'raw' in vals or 'datas' in vals:
            self._process_cloud_offload()
        return res

    def _process_cloud_offload(self):
        """Evaluates whether new or updated attachments qualify for cloud offloading."""
        if not get_config_param(self.env, 'cloud_attachment_storage.enabled', False, 'bool'):
            return

        min_size_kb = get_config_param(self.env, 'cloud_attachment_storage.min_size_kb', 50, 'int')
        bucket = get_config_param(self.env, 'cloud_attachment_storage.bucket')
        endpoint = get_config_param(self.env, 'cloud_attachment_storage.endpoint')
        access_key = get_config_param(self.env, 'cloud_attachment_storage.access_key')
        secret_key = get_config_param(self.env, 'cloud_attachment_storage.secret_key')
        region = get_config_param(self.env, 'cloud_attachment_storage.region', 'auto')
        delete_local = get_config_param(self.env, 'cloud_attachment_storage.delete_local', True, 'bool')
        provider = get_config_param(self.env, 'cloud_attachment_storage.provider', 'r2')

        if not (bucket and access_key and secret_key):
            return

        try:
            client = CloudStorageClient.get_client(
                endpoint_url=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                region_name=region if region != 'auto' else None,
            )
        except Exception as e:
            _logger.error("Cannot connect to cloud storage client: %s", e)
            return

        for record in self:
            if record.is_cloud_storage or not record.store_fname:
                continue

            file_size_kb = (record.file_size or 0) / 1024.0
            if file_size_kb < min_size_kb:
                continue

            db_name = self.env.cr.dbname
            object_key = f"{db_name}/{record.store_fname}"

            try:
                local_path = record._full_path(record.store_fname)
                if not os.path.exists(local_path):
                    continue

                with open(local_path, 'rb') as f:
                    CloudStorageClient.upload_object(
                        client=client,
                        bucket_name=bucket,
                        key=object_key,
                        data_stream=f,
                        mimetype=record.mimetype,
                    )

                record.write({
                    'is_cloud_storage': True,
                    'cloud_storage_key': object_key,
                    'cloud_storage_provider': provider,
                })

                if delete_local and os.path.exists(local_path):
                    count = self.search_count([('store_fname', '=', record.store_fname), ('is_cloud_storage', '=', False)])
                    if count == 0:
                        try:
                            os.remove(local_path)
                            _logger.info("Reclaimed local storage: deleted %s (offloaded to cloud)", local_path)
                        except OSError as e:
                            _logger.warning("Could not delete local file %s: %s", local_path, e)

            except Exception as e:
                _logger.error("Failed to offload attachment ID %s to cloud: %s", record.id, e)

    def unlink(self):
        """Cleans up objects in Cloud Storage upon attachment deletion."""
        bucket = get_config_param(self.env, 'cloud_attachment_storage.bucket')
        endpoint = get_config_param(self.env, 'cloud_attachment_storage.endpoint')
        access_key = get_config_param(self.env, 'cloud_attachment_storage.access_key')
        secret_key = get_config_param(self.env, 'cloud_attachment_storage.secret_key')
        region = get_config_param(self.env, 'cloud_attachment_storage.region', 'auto')

        client = None
        if bucket and access_key and secret_key:
            try:
                client = CloudStorageClient.get_client(
                    endpoint_url=endpoint,
                    access_key=access_key,
                    secret_key=secret_key,
                    region_name=region if region != 'auto' else None,
                )
            except Exception:
                pass

        keys_to_delete = []
        for record in self:
            if record.is_cloud_storage and record.cloud_storage_key:
                other_count = self.search_count([('id', 'not in', self.ids), ('cloud_storage_key', '=', record.cloud_storage_key)])
                if other_count == 0:
                    keys_to_delete.append(record.cloud_storage_key)

        res = super().unlink()

        if client and bucket:
            for key in keys_to_delete:
                try:
                    CloudStorageClient.delete_object(client, bucket, key)
                except Exception as e:
                    _logger.warning("Failed to delete cloud object %s: %s", key, e)

        return res
