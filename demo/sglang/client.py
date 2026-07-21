"""Smoke-test the SGLang server's OpenAI-compatible API."""

import argparse
import os

import requests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("SGLANG_HOST", "http://localhost:30000"))
    parser.add_argument("--model", default=os.environ.get("MODEL_REPO", "meta-llama/Llama-3.1-8B-Instruct"))
    parser.add_argument("--prompt", default="What is retrieval-augmented generation?")
    args = parser.parse_args()

    print(f"=== Models available at {args.host} ===")
    models = requests.get(f"{args.host}/v1/models", timeout=10)
    models.raise_for_status()
    print(models.json())

    print("\n=== Chat completion ===")
    resp = requests.post(
        f"{args.host}/v1/chat/completions",
        json={
            "model": args.model,
            "messages": [{"role": "user", "content": args.prompt}],
            "temperature": 0.7,
            "max_tokens": 256,
        },
        timeout=60,
    )
    resp.raise_for_status()
    print(resp.json()["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
