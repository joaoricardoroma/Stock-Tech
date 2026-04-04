.PHONY: help init clean seed clean-seed shell run

# Default target
.DEFAULT_GOAL := help

# Python executable (use virtual environment if active)
PYTHON = python3
PIP = pip

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

init: ## Initialize the environment (create venv, install reqs)
	$(PYTHON) -m venv venv
	./venv/bin/pip install -r requirements.txt
	@echo "Initialization complete. Run 'source venv/bin/activate' to activate."

clean: ## Erase the database completely
	@echo "Erasing database tables..."
	$(PYTHON) -c "import os; from app import app, db, init_db; app.app_context().push(); db.drop_all(); init_db()"
	@echo "Database erased."

seed: ## Run the seed script to populate data
	@echo "Running seed script..."
	$(PYTHON) seed_data.py

migrate: ## Add new DB columns (run once when app is stopped)
	@echo "Running DB migration..."
	$(PYTHON) -c "\
from app import app, db; \
from sqlalchemy import text, inspect; \
ctx = app.app_context(); ctx.push(); \
inspector = inspect(db.engine); \
cols = [c['name'] for c in inspector.get_columns('wine_purchases')]; \
conn = db.engine.connect(); \
conn.execute(text('ALTER TABLE wine_purchases ADD COLUMN invoice_image_path VARCHAR(500)')) if 'invoice_image_path' not in cols else print('invoice_image_path OK'); \
conn.execute(text('ALTER TABLE wine_purchases ADD COLUMN invoice_image_original VARCHAR(300)')) if 'invoice_image_original' not in cols else print('invoice_image_original OK'); \
conn.commit(); conn.close(); \
print('Migration complete!')"
	@echo "Migration done."

clean-seed: clean seed ## Erase database and re-seed it

shell: ## Open a python shell with app context (requires app.py structure to support it)
	$(PYTHON) -c "from app import app, db; app.app_context().push(); import code; code.interact(local=locals())"

run: ## Run the application
	$(PYTHON) app.py
