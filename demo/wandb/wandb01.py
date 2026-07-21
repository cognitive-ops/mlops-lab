# import modal
# app = modal.App("gpu-demo")
# @app.function(gpu="A10G")
# def check_gpu():
#     import subprocess
#     try:
#         subprocess.check_call(["nvidia-smi","--list-gpus"])
#     except Exception as e:
#         raise Exception("No GPU found")


import random

import wandb

# Start a new wandb run to track this script.
run = wandb.init(
    # Set the wandb entity where your project will be logged (generally your team name).
    entity="giaosucan-fpt",
    # Set the wandb project where this run will be logged.
    project="giaosucan-fpt",
    # Track hyperparameters and run metadata.
    config={
        "learning_rate": 0.02,
        "architecture": "CNN",
        "dataset": "CIFAR-100",
        "epochs": 10,
    },
)

# Simulate training.
epochs = 10
offset = random.random() / 5
for epoch in range(2, epochs):
    acc = 1 - 2**-epoch - random.random() / epoch - offset
    loss = 2**-epoch + random.random() / epoch + offset

    # Log metrics to wandb.
    run.log({"acc": acc, "loss": loss})

# Finish the run and upload any remaining data.
run.finish()