import boto3


class AWSSpotter:
    def __init__(self, instance_type='t2.medium', image_id='ami-0b898040803850657'):
        self.client = boto3.client('ec2',region_name='us-east-1')
        self.instance_type = instance_type
        self.image_id = image_id
        self.spot_request_id_map = {
            't2.medium': []
        }

    def get_price(self):
        prices=self.client.describe_spot_price_history(
            InstanceTypes=[self.instance_type],
            MaxResults=1,
            ProductDescriptions=['Linux/UNIX (Amazon VPC)'],
            AvailabilityZone='us-east-1a'
        )
        return prices['SpotPriceHistory'][0]['SpotPrice']

    def launch_spot_instances(self):
        price = self.get_price()
        response = self.client.request_spot_instances(
            SpotPrice = price,
            Type = 'one-time',
            LaunchSpecification = {
                'ImageId': self.image_id,
                'InstanceType': self.instance_type,
            }
        )
        self.spot_request_id_map[self.instance_type].append(response['SpotInstanceRequests'][0]['SpotInstanceRequestId'])
        return response

    def describe_spot_instance(self, spot_instance_request_ids=[]):
        if spot_instance_request_ids:
            response = self.client.describe_spot_instance_requests(
                DryRun=False,
                SpotInstanceRequestIds=spot_instance_request_ids,
            )
            return response
