output "instance_id" {
  value = aws_instance.gpu_instance.id
}

output "public_ip" {
  value = aws_instance.gpu_instance.public_ip
}

output "private_key_pem" {
  value     = tls_private_key.gpu_key.private_key_pem
  sensitive = true
}

output "ebs_volume_id" {
  value = aws_ebs_volume.ml_data_volume.id
  description = "ID of the 200GB EBS volume for ML data storage"
}

output "ebs_volume_device" {
  value = aws_volume_attachment.ml_data_attachment.device_name
  description = "Device name for the attached EBS volume"
}