import logging
import time

import boto3
import botocore


class AWSSpotScaler:
    """Keeps track of size of AWS Spot fleet and scales them up and down based on the max_price.

    Example Usage:
    spot_scaler = AWSSpotScaler(max_price='0.03', IAM_fleet_role="arn:aws:iam::123456789012:role/aws-ec2-spot-fleet-tagging-role")
    spot_scaler.run_spot_fleet_watcher()
    """
    def __init__(self,
                 instance_types=['m4.large', 'm4.xlarge', 'm4.2xlarge']
                 image_id='ami-0b898040803850657',
                 max_price=0.02,
                 IAM_fleet_role=''):
        self.client = boto3.client('ec2',region_name='us-east-1')
        self.instance_types = instance_types
        self.image_id = image_id

        for instance in instance_types:
            # Keeps track of spot instances
            self.spot_request_id_map = {
                instance: []
            }
            # Keeps track of spot fleets
            self.spot_fleet_id_map = {
                instance = None
            }
            # Keeps track of current capacity
            self.current_cap = {
                instance: 1
            }
        self.max_cap = 5
        self.min_cap = 1
        self.max_price = max_price
        self.IAM_fleet_role = IAM_fleet_role
        self.logger = logging.basicConfig(logging.BASIC_FORMAT)

    def get_price(self, instance_type):
        """Get the spot price of a specific instance type.
        """
        prices=self.client.describe_spot_price_history(
            InstanceTypes=[instance_type],
            MaxResults=1,
            ProductDescriptions=['Linux/UNIX (Amazon VPC)'],
            AvailabilityZone='us-east-1a'
        )
        return prices['SpotPriceHistory'][0]['SpotPrice']

    def run_spot_fleet_watcher(self):
        """Monitors and modifies the spot fleet every 10 minutes depending on the price

        Note: It requests a spot fleet on the very first run.
        """
        while True:
            try:
                for instance_type in self.instance_types:
                    price = self.get_price(instance_type)
                    # If this is the first time it's running, then request the spot fleet
                    if self.spot_fleet_id_map[instance_type] == None:
                        self.launch_spot_fleet(instance_type)
                        continue

                    # Check if the current price is less than our max price. If so, then increase spot fleet capacity
                    if price < self.max_price and self.current_cap[instance_type] <self.max_cap:
                        self.current_cap = self.max_cap
                        self.modify_spot_fleet(price,
                                               target_capacity=self.max_cap,
                                               spot_fleet_request_id=self.spot_fleet_id_map[instance_type])

                    # Else the current price is more than our max price and let's decrease the capacity of the spot instance fleet
                    else:
                        self.current_cap = self.min_cap
                        self.modify_spot_fleet(price,
                                           target_capacity=self.min_cap,
                                           spot_fleet_request_id=self.spot_fleet_id_map[instance_type])
           except botocore.exceptions.BotoCoreError as exp:
               self.logger.error('Error launching or modifying spot fleet', exp)

        # Check every 10 minutes
        time.sleep(600)

    def launch_spot_instances(self):
        """Launches spot instance for a set duration. This cannot be scaled up and down as desired.

        Spot fleet is better suited for that.
        """
        final_resp = []
        for instance_type in self.instance_types:
            price = self.get_price()
            response = self.client.request_spot_instances(
                DryRun=False,
                SpotPrice = price,
                Type = 'one-time',
                BlockDurationMinutes=60,
                InstanceCount=1,
                LaunchSpecification = {
                    'ImageId': self.image_id,
                    'InstanceType': self.instance_type,
                }
            )
            self.spot_request_id_map[self.instance_type].append(response['SpotInstanceRequests'][0]['SpotInstanceRequestId'])
            final_resp.append(response)
        return final_resp

    def launch_spot_fleet(self, instance_type):
        """Launches a spot fleet with a set max capacity
        """
        if self.IAM_fleet_role:
            price = self.get_price()
            response  = client.request_spot_fleet(
                SpotFleetRequestConfig={
                    'AllocationStrategy': 'lowestPrice',
                    'FulfilledCapacity':
                    'IamFleetRole': self.IAM_fleet_role,
                    'LaunchSpecifications': [
                        {
                            'ImageId': self.image_id,
                            'InstanceType': instance_type,
                        },
                    ],
                    'SpotPrice': price,
                    'TargetCapacity': self.max_cap,
                },
            )
            self.spot_fleet_id_map[instance_type] = response['SpotFleetRequestId']
            return response

    def modify_spot_fleet(self, price, target_capacity, spot_fleet_request_id):
        """Modifies the capacity (running instances) in a spot fleet
        """
        if self.IAM_fleet_role:
            response = client.modify_spot_fleet(
                ExcessCapacityTerminationPolicy='default',
                SpotFleetRequestId=spot_fleet_request_id,
                TargetCapacity=target_capacity,
            )
            return response

    def describe_spot_instance(self, spot_instance_request_ids=[]):
        """Describes a spot instance
        """
        if spot_instance_request_ids:
            response = self.client.describe_spot_instance_requests(
                DryRun=False,
                SpotInstanceRequestIds=spot_instance_request_ids,
            )
            return response
