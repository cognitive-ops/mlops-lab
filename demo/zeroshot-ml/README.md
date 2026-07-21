# Zero-Shot Learning Project

A comprehensive Python demonstration of zero-shot learning techniques using pre-trained models.

## Overview

Zero-shot learning enables machine learning models to recognize and classify objects, images, and text without having seen specific examples during training. This project demonstrates three main approaches:

### 1. **Text Classification** (`text_classification.py`)
- **Sentiment Analysis**: Classify text into sentiment categories without training
- **Intent Detection**: Identify user intents from queries
- **Natural Language Inference**: Determine if premises entail hypotheses
- Uses Facebook's BART model

### 2. **Image Classification** (`image_classification.py`)
- **Object Recognition**: Classify objects in images without training data
- **Attribute Classification**: Identify image attributes (lighting, composition, quality)
- **Object Detection**: Detect presence of objects with confidence scores
- Uses OpenAI's CLIP model (Vision-Language model)

### 3. **Semantic Search** (`semantic_search.py`)
- **Document Search**: Find relevant documents based on semantic similarity
- **Duplicate Detection**: Identify similar or duplicate texts
- **Text Clustering**: Group documents by semantic similarity
- Uses sentence-transformers embeddings

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

1. Clone or navigate to the project directory
2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

For semantic search clustering features, also install:
```bash
pip install scikit-learn
```

## Usage

### Run All Examples
```bash
python text_classification.py      # Text classification examples
python image_classification.py     # Image classification examples
python semantic_search.py          # Semantic search and clustering
```

### Individual Examples

#### Text Classification
```python
from text_classification import zero_shot_text_classification

results = zero_shot_text_classification()
```

#### Image Classification
```python
from image_classification import zero_shot_image_classification

# Classify a local image
results = zero_shot_image_classification("path/to/image.jpg")

# Or use a URL
results = zero_shot_image_classification("https://example.com/image.jpg")
```

#### Semantic Search
```python
from semantic_search import zero_shot_semantic_search

results = zero_shot_semantic_search()
```

## Output Files

Each script generates JSON results files:
- `text_classification_results.json` - Text classification results
- `image_classification_results.json` - Image classification results
- `semantic_search_results.json` - Semantic search and clustering results

## Models Used

### Text Models
- **facebook/bart-large-mnli**: BART model fine-tuned on Multi-Genre Natural Language Inference (MNLI) for zero-shot classification

### Vision Models
- **openai/clip-vit-base-patch32**: CLIP Vision Transformer for zero-shot image classification

### Embedding Models
- **sentence-transformers/all-MiniLM-L6-v2**: Efficient sentence embeddings for semantic search

## Key Advantages of Zero-Shot Learning

1. **No Training Required**: Use pre-trained models directly
2. **Flexible Labels**: Define new categories on-the-fly
3. **Fast Deployment**: No need for data collection or model training
4. **Domain Adaptation**: Works across different domains
5. **Cost Effective**: Reduces data annotation and training costs

## Performance Notes

- **First Run**: Models will be downloaded (~1-2 GB total) and cached locally
- **GPU Acceleration**: Uses CPU by default. Add GPU support by modifying device handling
- **Inference Speed**: Varies with model size and available hardware

## Extending the Examples

### Add GPU Support
```python
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)
```

### Custom Labels
Modify the candidate labels in each script to match your use case:
```python
candidate_labels = ["your", "custom", "labels", "here"]
```

### Batch Processing
Modify scripts to process multiple items in batches for better performance

## Troubleshooting

### Out of Memory
- Use a smaller model variant
- Process images in lower resolution
- Reduce batch size

### Model Download Issues
- Check internet connection
- Manually download models using transformers CLI:
  ```bash
  python -m transformers.cli.download_model facebook/bart-large-mnli
  ```

### CUDA Issues
- Install PyTorch with CUDA support: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`
- Fall back to CPU if issues persist

## References

- [Hugging Face Transformers](https://huggingface.co/docs/transformers/)
- [Zero-Shot Learning Paper](https://arxiv.org/abs/2104.14294)
- [CLIP: Learning Transferable Models For Computer Vision](https://arxiv.org/abs/2103.14030)
- [BART: Denoising Sequence-to-Sequence Pre-training](https://arxiv.org/abs/1910.13461)

## License

MIT License - Feel free to use for research and development

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.
