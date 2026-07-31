import os
import boto3
from botocore.exceptions import ClientError

def get_secret(key):
    secret_name = f"autonomous-agent/{key}"
    region_name = "ap-south-1"
    try:
        client = boto3.client("secretsmanager", region_name=region_name)
        response = client.get_secret_value(SecretId=secret_name)
        return response["SecretString"]
    except Exception:
        return os.getenv(key)
