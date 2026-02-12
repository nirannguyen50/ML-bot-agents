#!/bin/bash
# User data script for paper trading instances
# Auto-deploys system on instance launch

set -e

# Update system
apt-get update -y
apt-get upgrade -y

# Install Python and dependencies
apt-get install -y python3.9 python3-pip git
python3 -m pip install --upgrade pip

# Clone trading bot repository
git clone https://github.com/nirannguyen50/ML-bot-agents.git /opt/trading-bot
cd /opt/trading-bot

# Install Python requirements
pip3 install -r requirements.txt
pip3 install boto3 aioboto3 psutil

# Configure systemd service
cat > /etc/systemd/system/paper-trading.service << EOF
[Unit]
Description=Paper Trading System
After=network.target

[Service]
Type=exec
User=ubuntu
WorkingDirectory=/opt/trading-bot
ExecStart=/usr/bin/python3 /opt/trading-bot/workspace/paper_trading_system.py
Restart=always
RestartSec=10
Environment=AWS_REGION=ap-southeast-1

[Install]
WantedBy=multi-user.target
EOF

# Start service
systemctl daemon-reload
systemctl enable paper-trading.service
systemctl start paper-trading.service

# Install CloudWatch agent for monitoring
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i -E ./amazon-cloudwatch-agent.deb

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
  "metrics": {
    "metrics_collected": {
      "mem": {
        "measurement": ["mem_used_percent"],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": ["used_percent"],
        "metrics_collection_interval": 60,
        "resources": ["/"]
      }
    },
    "aggregation_dimensions": [["AutoScalingGroupName"]],
    "append_dimensions": {
      "AutoScalingGroupName": "\${aws:AutoScalingGroupName}",
      "InstanceId": "\${aws:InstanceId}"
    }
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Health check endpoint (for ALB)
python3 -m http.server 8080 &
echo "Instance setup completed at $(date)" >> /var/log/user-data.log