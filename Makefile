.PHONY: test news prices run

test:
	python -m unittest discover -s tests

# One-shot runs (same as the scheduled GitHub Actions job)
news:
	python -m src.run_task news

prices:
	python -m src.run_task market_prices

# Long-running mode with the in-process scheduler
run:
	python run.py
