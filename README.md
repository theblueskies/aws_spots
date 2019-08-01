# aws_spots

Scale up and down an AWS spot fleet depending on your max price.

Example Usage:  
```python
from aws_spotter import *
spot_scaler = AWSSpotScaler(max_price='0.03', IAM_fleet_role="arn:aws:iam::123456789012:role/aws-ec2-spot-fleet-tagging-role")  
spot_scaler.run_spot_fleet_watcher()  
```
