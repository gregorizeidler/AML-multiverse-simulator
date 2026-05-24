.PHONY: install install-frontend simulate simulate-fast simulate-full \
        api frontend test lint clean docker-up docker-down docker-logs

install:
	pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

simulate:
	python scripts/run_simulation.py

simulate-fast:
	python scripts/run_simulation.py --customers 500 --transactions 5000 --no-backtest

simulate-full:
	python scripts/run_simulation.py --customers 5000 --transactions 50000 --workers 6

api:
	uvicorn api.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	pytest tests/ -v --cov=src --cov-report=term-missing

test-fast:
	pytest tests/ -v -k "not ml_universe and not streaming and not backtest" --cov=src

lint:
	python -m ruff check src/ api/ scripts/ tests/ --fix 2>/dev/null || python -m flake8 src/ api/ scripts/ --max-line-length=100

clean:
	rm -rf data/output data/results __pycache__ .pytest_cache .coverage

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f
