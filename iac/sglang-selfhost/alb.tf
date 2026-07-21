# Application Load Balancer
resource "aws_lb" "main" {
  count              = var.enable_alb ? 1 : 0
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public.id]

  enable_deletion_protection = false

  tags = {
    Name = "${var.project_name}-alb"
  }
}

# Target Group for SGLang
resource "aws_lb_target_group" "sglang" {
  count       = var.enable_alb ? 1 : 0
  name        = "${var.project_name}-tg"
  port        = var.sglang_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "instance"

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = var.health_check_timeout
    interval            = var.health_check_interval
    path                = var.health_check_path
    port                = tostring(var.sglang_port)
    matcher             = "200-299"
  }

  tags = {
    Name = "${var.project_name}-tg"
  }
}

# Target Group Attachment
resource "aws_lb_target_group_attachment" "sglang" {
  count            = var.enable_alb ? 1 : 0
  target_group_arn = aws_lb_target_group.sglang[0].arn
  target_id        = aws_instance.llm.id
  port             = var.sglang_port
}

# ALB Listener
resource "aws_lb_listener" "http" {
  count             = var.enable_alb ? 1 : 0
  load_balancer_arn = aws_lb.main[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.sglang[0].arn
  }
}

# CloudWatch Alarm for ALB Unhealthy Hosts
resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_hosts" {
  count               = var.enable_alb && var.enable_cloudwatch_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-alb-unhealthy-hosts"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "Alert when ALB has unhealthy instances"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main[0].arn_suffix
    TargetGroup  = aws_lb_target_group.sglang[0].arn_suffix
  }
}

# CloudWatch Alarm for ALB Target Response Time
resource "aws_cloudwatch_metric_alarm" "alb_response_time" {
  count               = var.enable_alb && var.enable_cloudwatch_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-alb-high-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 5 # 5 seconds
  alarm_description   = "Alert when ALB response time is high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main[0].arn_suffix
  }
}
