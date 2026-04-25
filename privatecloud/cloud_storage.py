import os
import subprocess
import json
from pathlib import Path
from typing import Optional, List, Dict
import urllib.request
import urllib.error

BACKUP_ROOT = Path("backups")


def run_cmd(cmd, check=False, timeout=30):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check
        )
        return result
    except subprocess.TimeoutExpired:
        return type('obj', (object,), {'returncode': 124, 'stdout': '', 'stderr': 'Timeout'})()
    except Exception as e:
        return type('obj', (object,), {'returncode': 1, 'stdout': '', 'stderr': str(e)})()


def get_aws_credentials():
    return {
        'access_key': os.environ.get('AWS_ACCESS_KEY_ID'),
        'secret_key': os.environ.get('AWS_SECRET_ACCESS_KEY'),
        'region': os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
        'session_token': os.environ.get('AWS_SESSION_TOKEN'),
    }


def get_gcp_credentials():
    return {
        'project_id': os.environ.get('GCP_PROJECT_ID'),
        'service_account': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'),
    }


def get_azure_credentials():
    return {
        'account_name': os.environ.get('AZURE_STORAGE_ACCOUNT'),
        'account_key': os.environ.get('AZURE_STORAGE_KEY'),
        'connection_string': os.environ.get('AZURE_STORAGE_CONNECTION_STRING'),
    }


def check_s3_configured() -> bool:
    creds = get_aws_credentials()
    return bool(creds['access_key'] and creds['secret_key'])


def check_gcs_configured() -> bool:
    creds = get_gcp_credentials()
    return bool(creds['project_id'] and creds['service_account'])


def check_azure_configured() -> bool:
    creds = get_azure_credentials()
    return bool(creds['account_name'] and (creds['account_key'] or creds['connection_string']))


def upload_to_s3(local_path: str, bucket: str, key: Optional[str] = None) -> bool:
    if not check_s3_configured():
        print("⚠️  AWS credentials not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return False
    
    local_file = Path(local_path)
    if not local_file.exists():
        print(f"❌ File not found: {local_path}")
        return False
    
    creds = get_aws_credentials()
    if key is None:
        key = f"backups/{local_file.name}"
    
    print(f"📤 Uploading to S3: s3://{bucket}/{key}")
    
    try:
        import boto3
        from botocore.config import Config
        
        config = Config(max_pool_connections=10)
        s3 = boto3.client(
            's3',
            aws_access_key_id=creds['access_key'],
            aws_secret_access_key=creds['secret_key'],
            aws_session_token=creds['session_token'],
            region_name=creds['region'],
            config=config
        )
        
        s3.upload_file(str(local_file), bucket, key)
        print(f"✅ Uploaded to s3://{bucket}/{key}")
        return True
    except ImportError:
        print("⚠️  boto3 not installed. Install with: pip install boto3")
        return use_aws_cli_fallback(local_file, bucket, key, creds)
    except Exception as e:
        print(f"❌ S3 upload failed: {e}")
        return False


def use_aws_cli_fallback(local_file: Path, bucket: str, key: str, creds: dict) -> bool:
    env = os.environ.copy()
    env['AWS_ACCESS_KEY_ID'] = creds['access_key']
    env['AWS_SECRET_ACCESS_KEY'] = creds['secret_key']
    if creds['region']:
        env['AWS_DEFAULT_REGION'] = creds['region']
    if creds['session_token']:
        env['AWS_SESSION_TOKEN'] = creds['session_token']
    
    result = run_cmd(
        ['aws', 's3', 'cp', str(local_file), f's3://{bucket}/{key}'],
        timeout=300
    )
    
    if result.returncode == 0:
        print(f"✅ Uploaded to s3://{bucket}/{key} via AWS CLI")
        return True
    else:
        print(f"❌ AWS CLI upload failed: {result.stderr}")
        return False


def download_from_s3(bucket: str, key: str, local_path: Optional[str] = None) -> Optional[str]:
    if not check_s3_configured():
        print("⚠️  AWS credentials not configured")
        return None
    
    creds = get_aws_credentials()
    if local_path is None:
        local_path = str(BACKUP_ROOT / Path(key).name)
    
    print(f"📥 Downloading from S3: s3://{bucket}/{key}")
    
    try:
        import boto3
        s3 = boto3.client(
            's3',
            aws_access_key_id=creds['access_key'],
            aws_secret_access_key=creds['secret_key'],
            region_name=creds['region'],
        )
        
        s3.download_file(bucket, key, local_path)
        print(f"✅ Downloaded to {local_path}")
        return local_path
    except Exception as e:
        print(f"❌ S3 download failed: {e}")
        return None


def list_s3_backups(bucket: str, prefix: str = "backups/") -> List[Dict[str, str]]:
    if not check_s3_configured():
        return []
    
    creds = get_aws_credentials()
    
    try:
        import boto3
        s3 = boto3.client(
            's3',
            aws_access_key_id=creds['access_key'],
            aws_secret_access_key=creds['secret_key'],
            region_name=creds['region'],
        )
        
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        objects = response.get('Contents', [])
        
        return [
            {
                'key': obj['Key'],
                'size': obj['Size'],
                'modified': obj['LastModified'].isoformat() if 'LastModified' in obj else '',
                'storage': 's3',
            }
            for obj in objects
            if obj['Key'].endswith(('.tar.gz', '.tar.gz.age'))
        ]
    except Exception as e:
        print(f"❌ Failed to list S3 backups: {e}")
        return []


def delete_from_s3(bucket: str, key: str) -> bool:
    if not check_s3_configured():
        return False
    
    creds = get_aws_credentials()
    
    try:
        import boto3
        s3 = boto3.client(
            's3',
            aws_access_key_id=creds['access_key'],
            aws_secret_access_key=creds['secret_key'],
            region_name=creds['region'],
        )
        
        s3.delete_object(Bucket=bucket, Key=key)
        print(f"✅ Deleted s3://{bucket}/{key}")
        return True
    except Exception as e:
        print(f"❌ S3 delete failed: {e}")
        return False


def upload_to_gcs(local_path: str, bucket: str, destination: Optional[str] = None) -> bool:
    if not check_gcs_configured():
        print("⚠️  GCP credentials not configured. Set GCP_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS")
        return False
    
    local_file = Path(local_path)
    if not local_file.exists():
        print(f"❌ File not found: {local_path}")
        return False
    
    if destination is None:
        destination = f"backups/{local_file.name}"
    
    print(f"📤 Uploading to GCS: gs://{bucket}/{destination}")
    
    creds = get_gcp_credentials()
    
    try:
        from google.cloud import storage
        from google.oauth2 import service_account
        
        credentials = service_account.Credentials.from_service_account_file(creds['service_account'])
        client = storage.Client(project=creds['project_id'], credentials=credentials)
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(destination)
        blob.upload_from_filename(str(local_file))
        
        print(f"✅ Uploaded to gs://{bucket}/{destination}")
        return True
    except ImportError:
        print("⚠️  google-cloud-storage not installed. Install with: pip install google-cloud-storage")
        return use_gcloud_cli_fallback(local_file, bucket, destination, creds)
    except Exception as e:
        print(f"❌ GCS upload failed: {e}")
        return False


def use_gcloud_cli_fallback(local_file: Path, bucket: str, destination: str, creds: dict) -> bool:
    env = os.environ.copy()
    env['GOOGLE_APPLICATION_CREDENTIALS'] = creds['service_account']
    
    result = run_cmd(
        ['gcloud', 'storage', 'cp', str(local_file), f'gs://{bucket}/{destination}'],
        timeout=300
    )
    
    if result.returncode == 0:
        print(f"✅ Uploaded to gs://{bucket}/{destination} via gcloud CLI")
        return True
    else:
        print(f"❌ gcloud CLI upload failed: {result.stderr}")
        return False


def download_from_gcs(bucket: str, source: str, local_path: Optional[str] = None) -> Optional[str]:
    if not check_gcs_configured():
        return None
    
    creds = get_gcp_credentials()
    
    if local_path is None:
        local_path = str(BACKUP_ROOT / Path(source).name)
    
    print(f"📥 Downloading from GCS: gs://{bucket}/{source}")
    
    try:
        from google.cloud import storage
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file(creds['service_account'])
        client = storage.Client(project=creds['project_id'], credentials=credentials)
        bucket_obj = client.bucket(bucket)
        blob = bucket_obj.blob(source)
        blob.download_to_filename(local_path)
        
        print(f"✅ Downloaded to {local_path}")
        return local_path
    except Exception as e:
        print(f"❌ GCS download failed: {e}")
        return None


def upload_to_azure(local_path: str, container: str, blob_name: Optional[str] = None) -> bool:
    if not check_azure_configured():
        print("⚠️  Azure credentials not configured. Set AZURE_STORAGE_ACCOUNT and AZURE_STORAGE_KEY")
        return False
    
    local_file = Path(local_path)
    if not local_file.exists():
        print(f"❌ File not found: {local_path}")
        return False
    
    if blob_name is None:
        blob_name = f"backups/{local_file.name}"
    
    print(f"📤 Uploading to Azure: {container}/{blob_name}")
    
    try:
        from azure.storage.blob import BlobServiceClient
        
        conn_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        if conn_string:
            client = BlobServiceClient.from_connection_string(conn_string)
        else:
            creds = get_azure_credentials()
            account_url = f"https://{creds['account_name']}.blob.core.windows.net"
            from azure.core import credentials
            client = BlobServiceClient(account_url, credential=creds['account_key'])
        
        container_client = client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_name)
        
        with open(str(local_file), "rb") as f:
            blob_client.upload_blob(f, overwrite=True)
        
        print(f"✅ Uploaded to {container}/{blob_name}")
        return True
    except ImportError:
        print("⚠️  azure-storage-blob not installed. Install with: pip install azure-storage-blob")
        return False
    except Exception as e:
        print(f"❌ Azure upload failed: {e}")
        return False


def list_azure_blobs(container: str, prefix: str = "backups/") -> List[Dict[str, str]]:
    if not check_azure_configured():
        return []
    
    try:
        from azure.storage.blob import BlobServiceClient
        
        conn_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        if conn_string:
            client = BlobServiceClient.from_connection_string(conn_string)
        else:
            creds = get_azure_credentials()
            account_url = f"https://{creds['account_name']}.blob.core.windows.net"
            from azure.core import credentials
            client = BlobServiceClient(account_url, credential=creds['account_key'])
        
        container_client = client.get_container_client(container)
        blobs = container_client.list_blobs(name_starts_with=prefix)
        
        result = []
        for blob in blobs:
            if blob.name.endswith(('.tar.gz', '.tar.gz.age')):
                result.append({
                    'key': blob.name,
                    'size': blob.size,
                    'modified': blob.last_modified.isoformat() if hasattr(blob, 'last_modified') else '',
                    'storage': 'azure',
                })
        return result
    except Exception as e:
        print(f"❌ Failed to list Azure blobs: {e}")
        return []


def download_from_azure(container: str, blob_name: str, local_path: Optional[str] = None) -> Optional[str]:
    if not check_azure_configured():
        return None
    
    if local_path is None:
        local_path = str(BACKUP_ROOT / Path(blob_name).name)
    
    print(f"📥 Downloading from Azure: {container}/{blob_name}")
    
    try:
        from azure.storage.blob import BlobServiceClient
        
        conn_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        if conn_string:
            client = BlobServiceClient.from_connection_string(conn_string)
        else:
            creds = get_azure_credentials()
            account_url = f"https://{creds['account_name']}.blob.core.windows.net"
            from azure.core import credentials
            client = BlobServiceClient(account_url, credential=creds['account_key'])
        
        container_client = client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_name)
        
        with open(local_path, "wb") as f:
            f.write(blob_client.download_blob().readall())
        
        print(f"✅ Downloaded to {local_path}")
        return local_path
    except Exception as e:
        print(f"❌ Azure download failed: {e}")
        return None


def list_remote_backups(storage_type: str, bucket: str, prefix: str = "backups/") -> List[Dict[str, str]]:
    if storage_type == 's3':
        return list_s3_backups(bucket, prefix)
    elif storage_type == 'gcs':
        return [{'key': f'gs://{bucket}/{b}', 'storage': 'gcs'} for b in []]
    elif storage_type == 'azure':
        return list_azure_blobs(bucket, prefix)
    return []