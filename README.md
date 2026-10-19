# Odoo Cloud Attachment Storage

**Enterprise S3, Cloudflare R2 & MinIO Multi-Cloud Storage Optimizer for Odoo**

[![Odoo Version](https://img.shields.io/badge/Odoo-17.0%20%7C%2018.0%20%7C%2019.0%20%7C%2020.0-purple.svg)](https://apps.odoo.com)
[![License: OPL-1](https://img.shields.io/badge/License-OPL--1-blue.svg)](https://www.odoo.com/documentation/user/17.0/legal/licenses/licenses.html#odoo-proprietary-license-v1-0)
[![Python Dependencies](https://img.shields.io/badge/Dependencies-boto3%20%7C%20botocore-green.svg)](https://pypi.org/project/boto3/)

---

## Overview

As Odoo installations grow, binary attachments (CRM chatter, customer invoices, delivery receipts, PDFs) can rapidly consume hundreds of gigabytes of disk space, leading to:
1. Exorbitant SSD block storage costs on cloud providers (AWS EBS, DigitalOcean volumes).
2. Agonizingly slow database dumps and nightly backup failures.
3. High worker memory usage during large file downloads.

**Cloud Attachment Storage** seamlessly intercepts Odoo file writes and offloads them to S3-compatible object storage:
* **Cloudflare R2** (Zero egress fees, globally distributed)
* **Amazon Web Services (AWS S3)**
* **MinIO** (Self-hosted on-premise private clouds)
* **Wasabi Cloud Storage**

---

## Key Features

* **Transparent Operation:** Zero changes to user habits. Uploading and viewing files in CRM, Accounting, Sales, and Project chatter works out of the box.
* **100% Server Disk Reclaim:** Automatically cleans up local filestore copies once files are verified in cloud storage.
* **Direct Pre-Signed Download URLs:** Redirects downloads directly to S3/R2 CDN, offloading 100% of bandwidth and freeing up Odoo Python HTTP workers.
* **Batch Historical Migration Wizard:** 1-click wizard to safely migrate existing filestores to the cloud with batching and progress tracking.
* **Threshold Control:** Configurable size threshold (e.g., >50 KB) so small UI icons remain in memory while heavy documents go to the cloud.
* **Connection Tester:** Interactive test probe to verify bucket read/write permissions directly from General Settings.

---

## Installation & Setup

1. **Install Python Dependency:**
   ```bash
   pip install boto3 botocore
   ```

2. **Add to Addons Path:**
   Add this repository directory to your Odoo `addons_path` in `odoo.conf`:
   ```ini
   addons_path = /path/to/odoo/addons,/path/to/odoo_cloud_storage
   ```

3. **Install Module:**
   Update your Odoo apps list and install **`cloud_attachment_storage`**.

4. **Configure in General Settings:**
   * Go to **Settings -> General Settings -> Cloud Storage**.
   * Choose your provider (**Cloudflare R2**, **AWS S3**, **MinIO**, **Wasabi**).
   * Enter your **Bucket Name**, **Access Key ID**, and **Secret Access Key**.
   * Click **Test Bucket Connection** to verify read/write access.
   * Enable **Delete Local Filestore Copy** to reclaim disk space.

---

## Publishing to Odoo Apps Store (`apps.odoo.com`)

1. Create a remote GitHub repository: `sijo0218/odoo_cloud_storage`.
2. Push your branches (e.g. `20.0`, `18.0`, `17.0`).
3. Log in to [apps.odoo.com](https://apps.odoo.com) and link your GitHub repository.
4. Odoo will automatically index `cloud_attachment_storage` and publish the listing.
5. Recommended price: **€149.00** (under OPL-1 proprietary commercial license).

---

## Author & Support

* **Author:** Sijo Joseph S
* **GitHub:** [sijo0218](https://github.com/sijo0218)
* **Email:** `sijo0218@gmail.com`
