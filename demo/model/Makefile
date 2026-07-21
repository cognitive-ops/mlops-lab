.PHONY: help train serve docker-build docker-train docker-serve clean

help:
	@echo "Local workflow:"
	@echo "  make train         Train model locally (saves to ./artifacts/)"
	@echo "  make serve         Serve API locally on :8080"
	@echo ""
	@echo "Docker workflow:"
	@echo "  make docker-build  Build Docker images"
	@echo "  make docker-train  Train model inside Docker"
	@echo "  make docker-serve  Serve API via Docker on :8080"
	@echo ""
	@echo "  make clean         Remove ./artifacts/ directory"

# ── Local ──────────────────────────────────────────────────────────────────────

train:
	python train.py

serve:
	uvicorn app:app --host 0.0.0.0 --port 8080 --reload

# ── Docker ─────────────────────────────────────────────────────────────────────

docker-build:
	docker compose build

docker-train:
	docker compose run --rm train

docker-serve:
	docker compose up api

# ── Utility ────────────────────────────────────────────────────────────────────

clean:
	rm -rf artifacts/
