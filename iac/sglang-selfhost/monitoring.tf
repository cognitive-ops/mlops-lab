# EC2 Instance CPU Utilization
resource "aws_cloudwatch_metric_alarm" "cpu_utilization" {
  count               = var.enable_cloudwatch_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when EC2 CPU utilization is high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = aws_instance.llm.id
  }
}

# Log stream for SGLang server metrics
resource "aws_cloudwatch_log_stream" "sglang_metrics" {
  count          = var.enable_cloudwatch_monitoring ? 1 : 0
  name           = "sglang-metrics"
  log_group_name = aws_cloudwatch_log_group.sglang[0].name
}

# Dashboard for monitoring
resource "aws_cloudwatch_dashboard" "llm" {
  count          = var.enable_cloudwatch_monitoring ? 1 : 0
  dashboard_name = "${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", { stat = "Average" }],
            ["AWS/EC2", "NetworkIn", { stat = "Sum" }],
            ["AWS/EC2", "NetworkOut", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "EC2 Instance Metrics"
        }
      },
      {
        type = "log"
        properties = {
          query  = "fields @timestamp, @message | filter @message like /ERROR/ | stats count() by @message"
          region = var.aws_region
          title  = "Error Count"
        }
      }
    ]
  })
}
