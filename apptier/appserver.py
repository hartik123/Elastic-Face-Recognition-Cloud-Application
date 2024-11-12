import time
from flask import jsonify  # Comment out Flask if not used
import boto3
import botocore
from constants import REGION_NAME, S3_RESOURCE, SQS_RESOURCE, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_INPUT_BUCKET_NAME, S3_OUTPUT_BUCKET_NAME
import uuid
from model.face_recognition import face_match
import subprocess
import requests


# app = Flask(__name__)

s3_client = None
s3_input_bucket = S3_INPUT_BUCKET_NAME
s3_output_bucket = S3_OUTPUT_BUCKET_NAME
sqs_client = None
sqs_req_queue = None
sqs_res_queue = None

# Create S3 resource
def create_s3_resource():
    global s3_client
    s3_client = boto3.client(
        S3_RESOURCE,
        region_name=REGION_NAME,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

# Create SQS resource
def create_sqs_resource():
    global sqs_client
    sqs_client = boto3.client(
        SQS_RESOURCE,
        region_name=REGION_NAME,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

# Create S3 buckets
def create_s3_input_bucket():
    global s3_input_bucket
    s3_input_bucket = s3_client.create_bucket(Bucket=s3_input_bucket)

def create_s3_output_bucket():
    global s3_output_bucket
    s3_output_bucket = s3_client.create_bucket(Bucket=s3_output_bucket)

# Check if bucket exists
def check_bucket_exists(bucket_name):
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' exists.")
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            print(f"Bucket '{bucket_name}' does not exist.")
            return False
        else:
            print(f"Error checking bucket: {e}")
            return False

# Create SQS request queue
def create_sqs_req_queue():
    global sqs_req_queue
    response = sqs_client.create_queue(
        QueueName='1229588726-req-queue.fifo',
        Attributes={
            "FifoQueue": "true"
        }
    )
    sqs_req_queue = response.get("QueueUrl")
    
# Create SQS response queue
def create_sqs_res_queue():
    global sqs_res_queue
    response = sqs_client.create_queue(
        QueueName='1229588726-res-queue.fifo',
        Attributes={
            "FifoQueue": "true"
        }
    )
    sqs_res_queue = response.get("QueueUrl")

# Check if queue exists
def check_queue_exists(queue_name):
    try:
        response = sqs_client.get_queue_url(QueueName=queue_name)
        print(f"Queue '{queue_name}' exists. URL: {response['QueueUrl']}")
        return response['QueueUrl']
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
            print(f"Queue '{queue_name}' does not exist.")
            return None
        else:
            print(f"Error checking queue: {e}")
            return None

# Get object from S3 bucket
def get_s3_object(bucket_name, object_key, download_path):
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        with open(f'{download_path}/{object_key}', 'wb') as f:
            f.write(response['Body'].read())
        print(f"Object '{object_key}' downloaded from bucket '{bucket_name}' to '{download_path}/{object_key}'")
    except Exception as e:
        print(f"Error fetching object: {e}")

# Store text in S3 bucket
def store_text_in_s3(bucket_name, object_key, text_data):
    try:
        s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=text_data)
        print(f"Text data successfully uploaded to '{bucket_name}/{object_key}'")
    except Exception as e:
        print(f"Error uploading text to S3: {e}")
        
create_s3_resource()
    
# Ensure input and output buckets exist
if not check_bucket_exists(s3_input_bucket):
    create_s3_input_bucket()
if not check_bucket_exists(s3_output_bucket):
    create_s3_output_bucket()

# Prediction function
def predict_image():

    # Poll SQS queue for image name
    image_name = None
    while True:
        response = sqs_client.receive_message(
            QueueUrl=sqs_req_queue,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
            VisibilityTimeout=30
        )
        
        if 'Messages' in response and len(response['Messages']) > 0:
            
            request_id = response['Messages'][0]['Body'].split(":")[0]
            image_name = response['Messages'][0]['Body'].split(":")[1]
            print(f"Received image name: {image_name}")
            
            # Download image from S3
            download_path = "./images"
            get_s3_object(s3_input_bucket, image_name, download_path)
            time.sleep(5)
            
            # Predict using face_match function
            result = face_match(f'{download_path}/{image_name}', './model/data.pt')
            if result is None:
                return jsonify({"message": "No matching data found in the CSV"}), 200

            # Store the result in the output bucket
            store_text_in_s3(s3_output_bucket, image_name[:-4], result[0])

            # Send result to response SQS queue
            sqs_client.send_message(
                QueueUrl=sqs_res_queue,
                MessageBody=f"{request_id}:{image_name[:-4]}:{result[0]}",
                # MessageBody = "Testing message",
                MessageGroupId=request_id,
                MessageDeduplicationId = str(uuid.uuid4())
            )
            sqs_client.delete_message(
                QueueUrl=sqs_req_queue,
                ReceiptHandle=response['Messages'][0]['ReceiptHandle']
            )
        time.sleep(6)

# Initialize and create queues
create_sqs_resource()

sqs_req_queue = check_queue_exists('1229588726-req-queue.fifo')
if not sqs_req_queue:
    create_sqs_req_queue()

sqs_res_queue = check_queue_exists('1229588726-res-queue.fifo')
if not sqs_res_queue:
    create_sqs_res_queue()

if __name__ == '__main__':
    predict_image()
