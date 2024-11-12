from resources.EC2 import EC2

class EC2InstanceCreator:
    def __init__(self) -> None:
        self.ec2 = EC2()
    
    def create_EC2_instance(self):
        self.ec2.createEC2Instance()
        print("SUCCESS: INSTANCE CREATION SUCCESSFUL")
        
        
wt = EC2InstanceCreator()
wt.create_EC2_instance()