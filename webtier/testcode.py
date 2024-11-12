import boto3
from constants import REGION_NAME, S3_RESOURCE, SQS_RESOURCE, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


sqs_client = boto3.client(
    SQS_RESOURCE,
    region_name=REGION_NAME,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

response = sqs_client.send_message(
    QueueUrl='https://sqs.us-east-1.amazonaws.com/637423176713/1229588726-req-queue.fifo',
    MessageBody='Test message',
    MessageGroupId='1'
)
print(response)
