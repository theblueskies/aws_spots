import time

import boto3


class AWSSpotter:
    def __init__(self,
                 instance_type='t2.medium',
                 image_id='ami-0b898040803850657',
                 max_price=0.002,
                 IAM_fleet_role=''):
        self.client = boto3.client('ec2',region_name='us-east-1')
        self.instance_type = instance_type
        self.image_id = image_id
        self.spot_request_id_map = {
            't2.medium': []
        }
        self.spot_fleet_id_map = {
            't2.medium' = None
        }
        self.current_cap = {
            't2.medium': 1
        }
        self.max_cap = 5
        self.min_cap = 1
        self.max_price = max_price
        self.IAM_fleet_role = IAM_fleet_role

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

    def periodic_spot_fleet_watcher(self):
        """Monitors and modifies the spot fleet every 10 minutes depending on the price

        Note: It requests a spot fleet on the very first run.
        """
        while True:
            price = self.get_price(self.instance_type)
            # If this is the first time it's running, then request the spot fleet
            if self.spot_fleet_id_map[self.instance_type] == None:
                self.launch_spot_fleet()

            # Check if the current price is less than our max price. If so, then increase spot fleet capacity
            if price < self.max_price and self.current_cap[self.instance_type] <self.max_cap:
                self.modify_spot_fleet(price,
                                       target_capacity=self.max_cap,
                                       spot_fleet_request_id=self.spot_fleet_id_map[self.instance_type])

            # Else the current price is more than our max price and let's decrease the capacity of the spot instance fleet
            self.modify_spot_fleet(price,
                                   target_capacity=self.min_cap,
                                   spot_fleet_request_id=self.spot_fleet_id_map[self.instance_type])

        # Check every 10 minutes
        time.sleep(600)

    def launch_spot_instances(self):
        """Launches spot instance for a set duration. This cannot be scaled up and down as desired.

        Spot fleet is better suited for that.
        """
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
        return response

    def launch_spot_fleet(self):
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
                            'InstanceType': self.instance_type,
                        },
                    ],
                    'SpotPrice': price,
                    'TargetCapacity': self.max_cap,
                },
            )
            self.spot_fleet_id_map[self.instance_type] = response['SpotFleetRequestId']
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
