# -*- coding: utf-8 -*-
import werkzeug
from odoo import http
from odoo.http import request


class CloudAttachmentController(http.Controller):

    @http.route(['/cloud_storage/download/<int:attachment_id>'], type='http', auth='user')
    def download_cloud_attachment(self, attachment_id, **kwargs):
        """Redirects directly to pre-signed S3/R2 URL, offloading server bandwidth."""
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
        if not attachment.exists():
            return request.not_found()

        # Verify read access on the parent record
        attachment.check_access('read')

        if attachment.is_cloud_storage and attachment.cloud_storage_presigned_url:
            return werkzeug.utils.redirect(attachment.cloud_storage_presigned_url, 302)

        # Fallback to standard Odoo binary download
        return request.env['ir.binary']._get_stream_from(attachment).get_response()
