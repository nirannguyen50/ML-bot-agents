# AWS Paper Trading Infrastructure
# Auto-scaling group with CloudWatch monitoring

provider "aws" {
  region = "ap-southeast-1"
}

# VPC Configuration
resource "aws_vpc" "trading_vpc" {
  cidr_block = "10.0.0.0/16"
  enable_dns_support = true
  enable_dns_hostnames = true
  
  tags = {
    Name = "paper-trading-vpc"
    Environment = "production"
  }
}

# Auto Scaling Group
resource "aws_launch_template" "paper_trading_lt" {
  name_prefix = "paper-trading-"
  image_id = "ami-0c55b159cbfafe1f0"  # Ubuntu 20.04 LTS
  instance_type = "t3.medium"
  key_name = "trading-key"
  
  user_data = filebase64("${path.module}/user_data.sh")
  
  network_interfaces {
    associate_public_ip_address = true
    security_groups = [aws_security_group.trading_sg.id]
  }
  
  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "PaperTradingNode"
      Service = "TradingBot"
    }
  }
}

resource "aws_autoscaling_group" "trading_asg" {
  name = "paper-trading-asg"
  min_size = 2
  max_size = 10
  desired_capacity = 3
  health_check_type = "EC2"
  health_check_grace_period = 300
  
  launch_template {
    id = aws_launch_template.paper_trading_lt.id
    version = "$Latest"
  }
  
  vpc_zone_identifier = [aws_subnet.public_subnet_a.id, aws_subnet.public_subnet_b.id]
  
  tag {
    key = "Environment"
    value = "production"
    propagate_at_launch = true
  }
  
  # Auto-scaling policies
  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# CloudWatch Alarms for Auto-scaling
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name = "paper-trading-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods = "2"
  metric_name = "CPUUtilization"
  namespace = "AWS/EC2"
  period = "300"
  statistic = "Average"
  threshold = "80"
  alarm_description = "Scale up when CPU > 80% for 10 minutes"
  
  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.trading_asg.name
  }
  
  alarm_actions = [aws_autoscaling_policy.scale_up.arn]
}

# Kinesis Data Stream for Market Data
resource "aws_kinesis_stream" "market_data_stream" {
  name = "market-data-stream"
  shard_count = 2
  retention_period = 24
  
  shard_level_metrics = [
    "IncomingBytes",
    "OutgoingBytes",
    "IncomingRecords",
    "OutgoingRecords"
  ]
  
  tags = {
    Environment = "production"
    DataType = "market-feed"
  }
}

# Monitoring Integration with Existing System
resource "aws_cloudwatch_dashboard" "trading_dashboard" {
  dashboard_name = "paper-trading-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "paper-trading-asg"],
            [".", "NetworkIn", ".", "."],
            [".", "NetworkOut", ".", "."]
          ]
          period = 300
          stat = "Average"
          region = "ap-southeast-1"
          title = "Trading System Performance"
        }
      }
    ]
  })
}