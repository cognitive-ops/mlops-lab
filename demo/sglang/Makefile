.PHONY: help up down logs test clean

help:
	@echo "Docker workflow:"
	@echo "  make up      Start SGLang server on :30000 (GPU required)"
	@echo "  make down    Stop and remove the container"
	@echo "  make logs    Tail server logs"
	@echo "  make test    Run client.py smoke test against the running server"
	@echo ""
	@echo "  make clean   Remove local HF weights cache"

up:
	docker compose up -d sglang

down:
	docker compose down

logs:
	docker compose logs -f sglang

test:
	python client.py

clean:
	rm -rf .cache/
