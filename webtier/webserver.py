import time
from flask import Flask, jsonify, request
import boto3
import botocore
from constants import REGION_NAME, S3_RESOURCE, SQS_RESOURCE, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AMI_ID, INSTANCE_TYPE, S3_INPUT_BUCKET_NAME, S3_OUTPUT_BUCKET_NAME
import uuid
import base64
import math
import threading

app = Flask(__name__)

df_100 = None
df_1000 = None
results = {}

# Initialize AWS S3 and SQS resources
s3_client = None
s3_input_bucket = S3_INPUT_BUCKET_NAME
s3_output_bucket = S3_OUTPUT_BUCKET_NAME

sqs_client = None
sqs_req_queue_url = None
sqs_res_queue_url = None
ec2_client = None

instance_messages_assignment={}

def get_queue_message_count(queue_url):
    response = sqs_client.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(response['Attributes']['ApproximateNumberOfMessages'])

# Main function to manage scaling
def manage_scaling():
    current_instance_count = 0
    instances_running = []
    exponential_backoff_index = 0  # Used for exponential backoff
    
    while True:
        
        message_count = get_queue_message_count(sqs_req_queue_url)
        print(f"Messages in queue: {message_count}")

        # Calculate the required instances based on the message count
        required_instances = min(20, math.ceil((20 * message_count) / 20))

        # Scale up logic
        if current_instance_count < required_instances:
            instances_to_launch = 3 ** exponential_backoff_index
            
            # Ensure we do not exceed the required instances
            if instances_to_launch > (required_instances - current_instance_count):
                instances_to_launch = required_instances - current_instance_count
            
            instance_id_list = launch_instances(instances_to_launch)
            instances_running.extend(instance_id_list)
            current_instance_count += instances_to_launch
            print(f"Launched {instances_to_launch} instances, current count: {current_instance_count}")

            exponential_backoff_index += 1  # Increase index for exponential backoff on the next scale-up

        # Scale down logic
        elif current_instance_count > required_instances:
            instances_to_remove = []

            instances_to_terminate = min(3 ** exponential_backoff_index, current_instance_count - required_instances)
            instances_to_remove = instances_running[-instances_to_terminate:]

            
            # # Identify instances to terminate
            # for instance_id, message_count in list(instance_messages_assignment.items()):
            #     if message_count and message_count == 0 and instances_to_terminate >0:
            #         instances_to_terminate -= 1
            #         instances_to_remove.append(instance_id)
            #         del instance_messages_assignment[instance_id]

            if instances_to_remove:
                terminate_instances(instances_to_remove)
                instances_running = [instance for instance in instances_running if instance not in instances_to_remove]
                current_instance_count -= len(instances_to_remove)
                print(f"Terminated {len(instances_to_remove)} instances, current count: {current_instance_count}")

            # Decrease exponential backoff index after attempting to scale down
            exponential_backoff_index = max(0, exponential_backoff_index - 1)
            if(current_instance_count==0):
                exponential_backoff_index=0
        print("CURRENT INSTANCES COUNT", "REQUIRED INSTANCES", "EXPONENTIAL BACKOFF INDEX")
        print(f"\t{current_instance_count} | \t{required_instances} | \t{exponential_backoff_index}\n")
        time.sleep(20)  # Sleep for 30 seconds before checking again

def create_ec2_resource():
    global ec2_client
    ec2_client = boto3.client(
        "ec2", 
        region_name=REGION_NAME,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )

create_ec2_resource()

def name_instance(instance_id, instance_name):

    # Tag the instance with the provided name
    ec2_client.create_tags(
        Resources=[instance_id],
        Tags=[
            {
                'Key': 'Name',
                'Value': instance_name
            }
        ]
    )
    
def launch_instances(count):
    # user_data_script = """#!/bin/bash
    # sudo apt-get update
    # sudo apt-get install -y python3-pip
    # sudo apt install python3-virtualenv -y
    # sudo apt install python3.12-venv
    # cd /home/ubuntu/apptier
    # apt install python3.12-venv
    # python3 -m venv .venv
    # source .venv/bin/activate
    # pip install -r requirements.txt
    # nohup python3 appserver.py > appserver.log 2>&1 &
    # """
    user_data_script = """#!/bin/bash
    cd /home/ubuntu/apptier
    source .venv/bin/activate
    nohup python3 appserver.py &
    """
    print("LAUNCHING INSTANCE")
    try:
        instances = ec2_client.run_instances(
            ImageId=AMI_ID,
            InstanceType=INSTANCE_TYPE,
            MinCount=count,
            MaxCount=count,
            UserData=base64.b64encode(user_data_script.encode()).decode(),
            KeyName = "my_key_pair_hartik",
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags' : [{
                'Key': 'Name',
                'Value': 'Child'
                    }]
                }]
        )
        print(f"Launched {count} instances: {instances['Instances']}")
        instance_id_list = [instance.get("InstanceId") for instance in instances.get("Instances", [])]
    
        # Check if the list is empty and handle it
        if instance_id_list is None:
            print("No instances launched.")
            return []
        
        for instance_id in instance_id_list:
            print("INSTANCE ID-", instance_id)
            name_instance(instance_id=instance_id, instance_name= f"app-tier-instance-{instance_id}")
        
        return instance_id_list
    except Exception as e:
        print(f"Error launching instances: {e}")
        return None

def terminate_instances(instance_ids):
    if instance_ids:
        ec2_client.terminate_instances(InstanceIds=instance_ids)
        print(f"Terminated instances: {instance_ids}")

def create_s3_resource():
    global s3_client
    s3_client = boto3.client(
        S3_RESOURCE,
        region_name=REGION_NAME,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

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

def create_bucket(bucket_name):
    try:
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' created.")
    except Exception as e:
        print(f"Error creating bucket '{bucket_name}': {e}")

def create_sqs_resource():
    global sqs_client
    sqs_client = boto3.client(
        SQS_RESOURCE,
        region_name=REGION_NAME,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

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

def create_queue(queue_name):
    try:
        response = sqs_client.create_queue(
            QueueName=queue_name,
            Attributes={
                "FifoQueue": "true",
                # "ContentBasedDeduplication": "true"  # Uncomment if needed
            }
        )
        print(f"Queue '{queue_name}' created.")
        return response['QueueUrl']
    except Exception as e:
        print(f"Error creating queue '{queue_name}': {e}")
        return None

create_s3_resource()
create_sqs_resource()

# Ensure queues exist or create them
sqs_req_queue_url = check_queue_exists('1229588726-req-queue.fifo') or create_queue('1229588726-req-queue.fifo')
sqs_res_queue_url = check_queue_exists('1229588726-res-queue.fifo') or create_queue('1229588726-res-queue.fifo')

# Ensure buckets exist
if not check_bucket_exists(s3_input_bucket):
    create_bucket(s3_input_bucket)

if not check_bucket_exists(s3_output_bucket):
    create_bucket(s3_output_bucket)
    
# Start the scaling management in a separate thread or as a background task
scaling_thread = threading.Thread(target=manage_scaling, daemon=True)
scaling_thread.start()
    
@app.route('/test')
def home():
    return jsonify({"message": "Hello, World"})

# launch_instances(1)
@app.route('/', methods=['POST'])
def upload_file():
    # File upload handling
    if 'inputFile' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['inputFile']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    FileName = file.filename
    print(FileName)

    request_id = str(uuid.uuid4())
    
    # Send filename to SQS request queue
    try:
        number = FileName.split('_')[1].split('.')[0]
        sqs_client.send_message(
            QueueUrl=sqs_req_queue_url,
            MessageBody=f"{request_id}:{FileName}",
            MessageGroupId=str(uuid.uuid4()),
            MessageDeduplicationId=str(uuid.uuid4())
        )
    except Exception as e:
        print("Error", e)
        
    print("Message sent")
    # Upload file to S3 input bucket
    try:
        s3_client.put_object(Bucket=s3_input_bucket, Key=FileName, Body=file)
        print(f"File {FileName} uploaded to '{s3_input_bucket}'")
    except Exception as e:
        print(f"Error uploading file: {e}")
        return jsonify({"error": "Error uploading file"}), 500

    response = None
    # Wait for a response
    while True:
        response = sqs_client.receive_message(
            QueueUrl=sqs_res_queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
            VisibilityTimeout=30
        )

        if 'Messages' in response and len(response['Messages']) > 0:

            # # Update instance message assignment count
            # if "test" not in message_body:
            #     instance_messages_assignment[message_body] = instance_messages_assignment.get(message_body, 0) + 1
            #     # Delete the message from the queue
            #     sqs_client.delete_message(
            #         QueueUrl=sqs_res_queue_url,
            #         ReceiptHandle=message['ReceiptHandle']
            #     )
            # else:
            #     # Handle "test" messages
            #     instance_id = message_body.split(":")[0]
            #     if instance_id in instance_messages_assignment:
            #         instance_messages_assignment[instance_id] -= 1
            #     break
            break

        time.sleep(1)
    message = response['Messages'][0]
    # Now we can process the response
    if 'Messages' in response:
        message = response['Messages'][0]
        req_response_id = message["Body"].split(":")[0]
        message_parts = message["Body"].split(":")[1:3]
        output = ":".join(message_parts)

        # Clean up
        sqs_client.delete_message(
            QueueUrl=sqs_res_queue_url,
            ReceiptHandle=message['ReceiptHandle']
        )
        results[req_response_id] = output

        # Return the result
    while True:
        if request_id in results:
            return results[request_id]
    # return results[request_id]
        # print(request_id, "*****", req_response_id, "++++++", response['Messages'][0]["Body"].split(":")[1])
    # return "test_00:Paul"  
      
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, threaded=True)