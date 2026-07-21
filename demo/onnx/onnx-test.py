import torch
import torch.nn as nn
import onnx
import onnxruntime as ort

# Define a simple PyTorch model


class SimpleModel(nn.Module):
    def __init__(self):
        super(SimpleModel, self).__init__()
        self.fc = nn.Linear(3, 1)

    def forward(self, x):
        return self.fc(x)


# Create and export the model
model = SimpleModel()
dummy_input = torch.randn(1, 3)  # Example input tensor
torch.onnx.export(
    model,
    dummy_input,
    "simple_model.onnx",
    input_names=["input"],
    output_names=["output"],
    opset_version=11
)

print("Model exported to ONNX format.")

# Load and verify the ONNX model
onnx_model = onnx.load("simple_model.onnx")
onnx.checker.check_model(onnx_model)
print("ONNX model is valid.")

# Run inference with ONNX Runtime
ort_session = ort.InferenceSession("simple_model.onnx")
onnx_input = {"input": dummy_input.numpy()}
onnx_output = ort_session.run(None, onnx_input)

print("ONNX Runtime output:", onnx_output)
