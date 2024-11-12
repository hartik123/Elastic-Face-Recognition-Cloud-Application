import boto3
from .Constants import EC2_SERVICE, REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AMI_ID

class EC2:
    def __init__(self) -> None:
        self.ec2_client = boto3.client(
            EC2_SERVICE,
            region_name = REGION,
            aws_access_key_id = AWS_ACCESS_KEY_ID,
            aws_secret_access_key = AWS_SECRET_ACCESS_KEY
        )
        
    def createEC2Instance(self):
        ec2_res = boto3.resource(EC2_SERVICE, 
        region_name = REGION,
        aws_access_key_id = AWS_ACCESS_KEY_ID,
        aws_secret_access_key = AWS_SECRET_ACCESS_KEY
        )
        self.ec2_instance = ec2_res.create_instances(
            ImageId = AMI_ID,
            MinCount=1,
            MaxCount=1,
            InstanceType="t2.micro",
            TagSpecifications = [{
                'ResourceType': 'instance',
                'Tags': [{
                    'Key': 'Name',
                    'Value': 'web-instance'
                }]
            }]
        )
        print("EC2 Instance created successfully")
        print(self.ec2_instance)
        
    # def setEC2InstanceTags(self):
    #     CreateTagsRequest createTagsRequest = new CreateTagsRequest().withResources(
    #           self.ec2_instance.getInstanceId())
    #          .withTags(new Tag("Name", "Your Tag Name"));
    #     self.ec2_client.createTags(createTagsRequest);