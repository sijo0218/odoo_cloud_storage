# -*- coding: utf-8 -*-
import io
import logging

_logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.client import Config
    from botocore.exceptions import ClientError, EndpointConnectionError
except ImportError:
    boto3 = None
    Config = None
    ClientError = Exception
    EndpointConnectionError = Exception
    _logger.warning("boto3 or botocore is not installed. Cloud Attachment Storage requires 'pip install boto3'.")


class CloudStorageClient:
    """Thread-safe S3-compatible cloud storage adapter (AWS S3, Cloudflare R2, MinIO, Wasabi)."""

    @classmethod
    def get_client(cls, endpoint_url=None, access_key=None, secret_key=None, region_name=None):
        if not boto3:
            raise RuntimeError("The 'boto3' library is required for cloud attachment storage. Please install it via pip.")

        config = Config(
            signature_version='s3v4',
            retries={'max_attempts': 3, 'mode': 'standard'},
            connect_timeout=5,
            read_timeout=30,
        )

        client_kwargs = {
            'service_name': 's3',
            'aws_access_key_id': access_key or None,
            'aws_secret_access_key': secret_key or None,
            'config': config,
        }
        if endpoint_url:
            client_kwargs['endpoint_url'] = endpoint_url
        if region_name:
            client_kwargs['region_name'] = region_name

        return boto3.client(**client_kwargs)

    @classmethod
    def test_bucket_connection(cls, endpoint_url, access_key, secret_key, bucket_name, region_name=None):
        """Validates credentials and read/write permissions on the target bucket."""
        try:
            client = cls.get_client(endpoint_url, access_key, secret_key, region_name)
            # 1. Check bucket access
            client.head_bucket(Bucket=bucket_name)

            # 2. Write test probe
            test_key = '.odoo_cloud_probe_test'
            client.put_object(
                Bucket=bucket_name,
                Key=test_key,
                Body=b'Odoo Cloud Storage Probe Verification',
                ContentType='text/plain',
            )

            # 3. Read back test probe
            resp = client.get_object(Bucket=bucket_name, Key=test_key)
            body = resp['Body'].read()
            if body != b'Odoo Cloud Storage Probe Verification':
                raise RuntimeError("Integrity check failed: read content did not match probe.")

            # 4. Clean up test probe
            client.delete_object(Bucket=bucket_name, Key=test_key)
            return True, "Connection successful! Bucket is readable and writable."
        except ClientError as e:
            err_code = e.response.get('Error', {}).get('Code', 'Unknown')
            err_msg = e.response.get('Error', {}).get('Message', str(e))
            return False, f"S3 Client Error [{err_code}]: {err_msg}"
        except EndpointConnectionError as e:
            return False, f"Could not connect to storage endpoint '{endpoint_url}': {str(e)}"
        except Exception as e:
            return False, f"Verification failed: {str(e)}"

    @classmethod
    def upload_object(cls, client, bucket_name, key, data_stream, mimetype=None):
        """Uploads a stream to the bucket with content type."""
        extra_args = {}
        if mimetype:
            extra_args['ContentType'] = mimetype

        if isinstance(data_stream, bytes):
            data_stream = io.BytesIO(data_stream)

        client.upload_fileobj(
            Fileobj=data_stream,
            Bucket=bucket_name,
            Key=key,
            ExtraArgs=extra_args if extra_args else None
        )

    @classmethod
    def download_object(cls, client, bucket_name, key):
        """Downloads object bytes from S3/R2."""
        buffer = io.BytesIO()
        client.download_fileobj(Bucket=bucket_name, Key=key, Fileobj=buffer)
        buffer.seek(0)
        return buffer.read()

    @classmethod
    def generate_presigned_url(cls, client, bucket_name, key, expiration=3600):
        """Generates a secure, temporary download URL."""
        return client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=expiration
        )

    @classmethod
    def delete_object(cls, client, bucket_name, key):
        """Deletes object from bucket."""
        client.delete_object(Bucket=bucket_name, Key=key)


def get_config_param(env, key, default='', param_type='str'):
    """Universal configuration getter compatible with both Odoo 17/18/19 (get_param) and Odoo 20+ (typed getters)."""
    ICP = env['ir.config_parameter'].sudo()
    if hasattr(ICP, 'get_str'):
        if param_type == 'bool':
            return ICP.get_bool(key, default=bool(default))
        elif param_type == 'int':
            return ICP.get_int(key, default=int(default or 0))
        return ICP.get_str(key, default=str(default or ''))
    elif hasattr(ICP, 'get_param'):
        val = ICP.get_param(key, default)
        if param_type == 'bool':
            return val in ('True', 'true', '1', True)
        elif param_type == 'int':
            try:
                return int(val or 0)
            except (ValueError, TypeError):
                return int(default or 0)
        return val if val is not None else default
    return default
