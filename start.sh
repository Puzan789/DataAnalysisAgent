

# Activate virtual environment
source .venv/bin/activate

# Kill any existing process on port 8000 (optional)
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Run with valid options
uvicorn amain:app --reload  --timeout-keep-alive 30 --host 0.0.0.0 --port 8000
