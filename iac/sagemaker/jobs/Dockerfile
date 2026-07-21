FROM pytorch/pytorch:1.13.0-cuda11.6-cudnn8-devel

RUN pip install wandb tensorboard

# Install Python dependencies
RUN pip install --no-cache-dir numpy==1.26.4 \
    scipy tqdm coloredlogs easydict nibabel open3d==0.14.1 \
    scikit-learn einops ipdb tensorboard tensorboardX wandb

RUN pip install small-gicp==1.0.0
RUN pip install botocore==1.40.21 "urllib3<1.27,>=1.25.4"

WORKDIR /workspace
