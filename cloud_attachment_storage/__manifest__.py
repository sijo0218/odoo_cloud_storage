# -*- coding: utf-8 -*-
{
    'name': 'Cloud Attachment Storage (AWS S3, Cloudflare R2 & MinIO)',
    'version': '18.0.1.0.0',
    'category': 'Extra Tools/Document Management',
    'summary': 'Offload attachments to AWS S3, Cloudflare R2, MinIO, or Wasabi. Drastically reduce disk bloat and backup time.',
    'description': """
Cloud Attachment Storage & Filestore Optimizer for Odoo
========================================================
Seamlessly offload Odoo binary attachments (CRM chatter, Sales invoices, Accounting documents, Purchase receipts)
to high-speed, cost-effective S3-compatible cloud object storage providers:
- **Cloudflare R2** (Zero egress fees)
- **Amazon Web Services (AWS S3)**
- **MinIO** (Self-hosted S3-compatible storage)
- **Wasabi Cloud Storage**
- **DigitalOcean Spaces**

Key Features:
-------------
* **Transparent Offloading:** Intercepts attachment uploads and routes them directly to cloud storage.
* **Dual Read Mode:** Transparently streams from cloud storage or serves pre-signed direct URLs for lightning-fast downloads.
* **1-Click Historical Migration Wizard:** Easily migrate existing local filestore attachments to the cloud with progress indicators.
* **Storage Deduplication:** Retains Odoo's SHA-1 content hashing to prevent duplicate cloud uploads.
* **Threshold & Model Rules:** Selectively offload files larger than a specified size or target specific models (e.g., `crm.lead`, `account.move`).
* **Connection Tester:** Verify bucket credentials, endpoints, and write permissions directly from General Settings.
    """,
    'author': 'Sijo Joseph S',
    'website': 'https://github.com/sijo0218',
    'license': 'OPL-1',
    'price': 149.00,
    'currency': 'EUR',
    'depends': ['base', 'mail', 'base_setup'],
    'external_dependencies': {
        'python': ['boto3', 'botocore'],
    },
    'data': [
        'security/ir.access.csv',
        'views/res_config_settings_views.xml',
        'views/ir_attachment_views.xml',
        'wizard/attachment_migration_wizard_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
