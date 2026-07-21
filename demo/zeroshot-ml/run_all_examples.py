"""
Main runner script for all zero-shot learning examples
Orchestrates execution of all demonstrations
"""

import sys
import json
from pathlib import Path


def run_example(module_name, function_name=None):
    """Run a specific example module"""
    print(f"\n{'='*60}")
    print(f"Running: {module_name}")
    print(f"{'='*60}\n")

    try:
        if module_name == "text":
            from text_classification import (
                zero_shot_text_classification,
                zero_shot_intent_classification,
                zero_shot_nli_classification
            )
            text_results = zero_shot_text_classification()
            intent_results = zero_shot_intent_classification()
            nli_results = zero_shot_nli_classification()
            return {
                "text_classification": text_results,
                "intent_classification": intent_results,
                "nli_classification": nli_results
            }

        elif module_name == "image":
            from image_classification import (
                zero_shot_image_attributes,
                zero_shot_object_detection_style
            )
            print("Note: Image classification requires downloading CLIP model (~340MB)\n")
            attr_results = zero_shot_image_attributes()
            obj_results = zero_shot_object_detection_style()
            return {
                "image_attributes": attr_results,
                "object_detection": obj_results
            }

        elif module_name == "semantic":
            from semantic_search import (
                zero_shot_semantic_search,
                zero_shot_duplicate_detection,
                zero_shot_clustering
            )
            search_results = zero_shot_semantic_search()
            dup_results = zero_shot_duplicate_detection()
            cluster_results = zero_shot_clustering()
            return {
                "semantic_search": search_results,
                "duplicate_detection": dup_results,
                "clustering": cluster_results
            }

        else:
            print(f"Unknown module: {module_name}")
            return None

    except ImportError as e:
        print(f"Import Error: {e}")
        print("Please install required packages: pip install -r requirements.txt")
        return None
    except Exception as e:
        print(f"Error running {module_name}: {e}")
        return None


def main():
    """Main execution function"""
    print("\n" + "="*60)
    print("ZERO-SHOT LEARNING - MAIN RUNNER")
    print("="*60)

    if len(sys.argv) > 1:
        # Run specific example
        example = sys.argv[1].lower()
        if example in ["text", "image", "semantic"]:
            results = run_example(example)
            if results:
                output_file = f"{example}_results.json"
                with open(output_file, "w") as f:
                    json.dump(results, f, indent=2)
                print(f"\nResults saved to: {output_file}")
        else:
            print(f"Unknown example: {example}")
            print("Available examples: text, image, semantic")
    else:
        # Run all examples
        print("\nRunning all examples...\n")

        all_results = {}

        # Text Classification
        text_results = run_example("text")
        if text_results:
            all_results["text"] = text_results

        # Semantic Search
        semantic_results = run_example("semantic")
        if semantic_results:
            all_results["semantic"] = semantic_results

        # Image Classification (optional - requires CLIP download)
        user_input = input(
            "\nRun image classification example? (requires ~340MB download) [y/n]: ").strip().lower()
        if user_input == 'y':
            image_results = run_example("image")
            if image_results:
                all_results["image"] = image_results

        # Save all results
        with open("all_results.json", "w") as f:
            json.dump(all_results, f, indent=2)

        print("\n" + "="*60)
        print("All results saved to: all_results.json")
        print("="*60)

        # Print summary
        print("\nSummary:")
        for category in all_results.keys():
            print(f"  - {category}: ✓ Completed")


if __name__ == "__main__":
    main()
