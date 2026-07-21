resource "aws_route53_record" "mlflow_dns" {
  provider = aws.acme_vpc
  zone_id  = "Z07188222Y1QARD0HXXBQ"
  name     = "mlflow.acmedev.com"
  type     = "A"
  ttl      = 300
  records  = [aws_eip.mlflow_eip.public_ip]


}