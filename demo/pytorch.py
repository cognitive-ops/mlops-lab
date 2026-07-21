# First, import PyTorch
import torch
### Generate some data
torch.manual_seed(7) # Set the random seed so things are predictable
# Features are 5 random normal variables
features = torch.randn((1, 5))
# create argument a is Tensor([1,2])
a = torch.Tensor([1,2])
print("Features:", features)