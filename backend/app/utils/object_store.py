import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
load_dotenv()

class ObjectStore:
    def __init__(self):
        self.client = boto3.client("s3",
        endpoint_url = os.getenv("S3_ENDPOINT"),
        aws_access_key_id = os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key = os.getenv("S3_SECRET_KEY"),
        region_name = os.getenv("S3_REGION")
        )

    def ensure_bucket_exists(self):
        bucket_name = os.getenv("S3_BUCKET_NAME")
        try:
            self.client.head_bucket(Bucket = bucket_name)
        except ClientError:
            self.client.create_bucket(Bucket = bucket_name)
    def upload_fileobj(self,fileobj,key:str,content_type:str):
        self.client.upload_fileobj(Fileobj = fileobj,Key = key,Bucket = os.getenv("S3_BUCKET_NAME"),ExtraArgs = {"ContentType":content_type} )
object_store = ObjectStore()


