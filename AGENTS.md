# AGENTS.md (Tailored for Midjourney v3 Studio - Repo-Root Scope)

## Overview
- Detected setup: python, ai_ml, cuda
- Total repositories: 1 (local project; initialize Git if needed for tracking)
- Monorepo structure: No
- Hardware: Ryzen 7 (8 cores/16 threads), RTX 4060 Ti (4GB VRAM)
- GPU Optimization: Enabled (CUDA/TensorRT for potential local inference)
- Secrets in Env: Detected - Review .env handling (e.g., API tokens)

## Setup and Development (Python/Streamlit)
- Activation: `venv\Scripts\activate` (or `conda activate base` for Miniconda integration)
- Installation: `pip install -r requirements.txt`
- Run: `streamlit run app.py` (opens at http://localhost:8501)
- Testing: `pytest -n 8 --cov` (parallel for 8 cores; focus on API mocks)

## AI/ML-Specific Rules (Midjourney API Optimized)
- Validate secrets in `.streamlit/secrets.toml` (api_token, discord_token) before endpoint calls.
- Prompt construction: Append parameters programmatically (e.g., `--ar 16:9 --v 7 --s 250`).
- Job polling: Use 3-second non-blocking intervals; handle 429 (rate limit) with 10-30s retries.
- File uploads: Enforce <10MB limits for blends/describes; use `multipart/form-data` with `imageBlob`.
- Error handling: Check for 596 (moderation) via Discord; reset channel if needed.
- GPU fallback: For extensions (e.g., local stylize), limit batch_size <=4 to avoid OOM on 4GB VRAM; validate with `nvidia-smi`.

## Conventions
- Conventional Commits (e.g., `feat:`, `fix:`).
- Exclude secrets from commits; provide `.env.example` or `secrets.toml.example`.

## Definition of Completion
Before proposing changes:
1. Linting/type checks (e.g., `pylint` or `mypy`).
2. Tests with >80% coverage (include API endpoint mocks).
3. Resource validation (no OOM on 48GB RAM/4GB VRAM; simulate concurrent jobs <= subscription limit).
4. `git commit -m "feat: ..."`.

## Pull Request Guidelines
- Title: `<type>(scope): summary` (e.g., `fix(api): enhance polling for 429 errors`).
- Body: Changes overview, test results, rate-limit/moderation impact, rollback strategy.