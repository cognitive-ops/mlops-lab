"""
Zero-Shot Image Classification Example
Uses CLIP model for zero-shot image classification
"""

from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image
import json
import requests
from io import BytesIO
import os


def download_image(url):
    """Download image from URL"""
    response = requests.get(url, timeout=10)
    return Image.open(BytesIO(response.content)).convert("RGB")


def zero_shot_image_classification(image_path_or_url):
    """
    Classify an image into predefined categories without training
    """
    # Load CLIP model and processor
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    # Load image
    if image_path_or_url.startswith("http"):
        image = download_image(image_path_or_url)
    else:
        image = Image.open(image_path_or_url).convert("RGB")

    # Define candidate labels for classification
    candidate_labels = [
        "a cat",
        "a dog",
        "a bird",
        "a car",
        "a person",
        "a landscape",
        "a building",
        "food"
    ]

    # Create text inputs
    inputs = processor(
        text=candidate_labels,
        images=image,
        return_tensors="pt",
        padding=True
    )

    # Get predictions
    with torch.no_grad():
        outputs = model(**inputs)
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=1)

    # Display results
    print("=" * 60)
    print("ZERO-SHOT IMAGE CLASSIFICATION")
    print("=" * 60)
    print(f"Image: {image_path_or_url}")
    print(f"Image size: {image.size}\n")

    # Sort predictions by probability
    sorted_indices = torch.argsort(probs[0], descending=True)

    results = []
    for idx in sorted_indices:
        label = candidate_labels[idx]
        prob = probs[0][idx].item()
        print(f"{label:20s} : {prob:.4f}")

        results.append({
            "label": label,
            "probability": float(prob)
        })

    return results


def zero_shot_image_attributes():
    """
    Classify image attributes without training
    """
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    # Use a sample image URL (landscape)
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/GoldenGateBridge-001.jpg/1280px-GoldenGateBridge-001.jpg"

    try:
        image = download_image(image_url)
    except Exception as e:
        print(f"Could not download image: {e}")
        print("Using placeholder instead...")
        # Create a simple placeholder image
        image = Image.new('RGB', (224, 224), color=(73, 109, 137))

    # Define attributes to classify
    attributes = [
        "a bright sunny day",
        "a dark cloudy day",
        "a rural landscape",
        "an urban landscape",
        "a peaceful scene",
        "a chaotic scene",
        "high quality photo",
        "low quality photo"
    ]

    inputs = processor(
        text=attributes,
        images=image,
        return_tensors="pt",
        padding=True
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)

    print("\n" + "=" * 60)
    print("ZERO-SHOT IMAGE ATTRIBUTE CLASSIFICATION")
    print("=" * 60)
    print(f"Image URL: {image_url}\n")

    sorted_indices = torch.argsort(probs[0], descending=True)

    results = []
    for idx in sorted_indices:
        attribute = attributes[idx]
        prob = probs[0][idx].item()
        print(f"{attribute:30s} : {prob:.4f}")

        results.append({
            "attribute": attribute,
            "probability": float(prob)
        })

    return results


def zero_shot_object_detection_style():
    """
    Use CLIP for object presence classification
    """
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    # Sample image
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/1280px-Cat_November_2010-1a.jpg"

    try:
        image = download_image(image_url)
    except Exception as e:
        print(f"Could not download image: {e}")
        image = Image.new('RGB', (224, 224), color=(73, 109, 137))

    # Object classes to detect
    objects = [
        "a cat",
        "a dog",
        "a person",
        "a car",
        "a tree",
        "water",
        "a building",
        "a bicycle"
    ]

    inputs = processor(
        text=objects,
        images=image,
        return_tensors="pt",
        padding=True
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)

    print("\n" + "=" * 60)
    print("ZERO-SHOT OBJECT DETECTION (Style)")
    print("=" * 60)
    print(f"Image URL: {image_url}\n")

    # Create presence detection (threshold-based)
    threshold = 0.3
    detected_objects = []

    for idx, obj in enumerate(objects):
        prob = probs[0][idx].item()
        if prob > threshold:
            detected_objects.append({"object": obj, "confidence": float(prob)})
            print(f"✓ DETECTED: {obj:20s} (confidence: {prob:.4f})")
        else:
            print(f"✗ Not detected: {obj:20s} (confidence: {prob:.4f})")

    return detected_objects


def main():
    """Run zero-shot image classification examples"""
    print("\n" + "=" * 60)
    print("ZERO-SHOT IMAGE LEARNING DEMONSTRATION")
    print("=" * 60)

    # Note: This requires downloading pre-trained models on first run
    print("\nNote: First run will download CLIP models (~340MB)")
    print("This may take a few minutes...\n")

    try:
        # Run attribute classification
        attribute_results = zero_shot_image_attributes()

        # Run object detection style classification
        object_results = zero_shot_object_detection_style()

        # Save results
        results = {
            "image_attributes": attribute_results,
            "object_detection": object_results
        }

        with open("image_classification_results.json", "w") as f:
            json.dump(results, f, indent=2)

        print("\n" + "=" * 60)
        print("Results saved to image_classification_results.json")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure you have torch and transformers installed:")
        print("  pip install -r requirements.txt")


if __name__ == "__main__":
    main()
