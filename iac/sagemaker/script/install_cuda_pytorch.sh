#!/bin/bash

set -e

echo "Updating system packages..."
sudo yum update -y

echo "Installing development tools and dependencies..."
sudo yum groupinstall -y "Development Tools"
sudo yum install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r) gcc gcc-c++ wget dkms

echo "Downloading CUDA 11.7 runfile installer..."
wget https://developer.download.nvidia.com/compute/cuda/11.7.0/local_installers/cuda_11.7.0_515.43.04_linux.run

echo "Making installer executable..."
chmod +x cuda_11.7.0_515.43.04_linux.run

echo "Installing CUDA 11.7..."
sudo ./cuda_11.7.0_515.43.04_linux.run --silent --toolkit

echo "Exporting environment variables..."
echo 'export PATH=/usr/local/cuda-11.7/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-11.7/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

echo "Verifying nvcc..."
nvcc --version

echo "Installing Miniconda (for Python and PyTorch)..."
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
bash miniconda.sh -b -p $HOME/miniconda
export PATH="$HOME/miniconda/bin:$PATH"
echo 'export PATH="$HOME/miniconda/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

echo "Creating conda environment for PyTorch..."
conda create -y -n torch113 python=3.9
conda activate torch113

echo "Installing PyTorch 1.13.1 with CUDA 11.7..."
conda install -y pytorch==1.13.1 torchvision torchaudio pytorch-cuda=11.7 -c pytorch -c nvidia

echo "Verifying PyTorch GPU support..."
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('CUDA version:', torch.version.cuda)"

echo "Installation complete. To activate environment, run: conda activate torch113"
