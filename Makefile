####################################################################################################################
# Setup containers to run Airflow

docker-spin-up:
	docker compose build && docker compose up airflow-init && docker compose up --build -d 

perms:
    @if command -v uname >/dev/null 2>&1; then OS=$$(uname -s); else OS=Unknown; fi; \
    if echo "$$OS" | grep -Eqi "mingw|msys|cygwin"; then \
        # Windows / Git-Bash: create dirs, skip chmod (PowerShell alternative attempted if mkdir fails) \
        mkdir -p logs plugins temp dags tests data  || powershell -Command "New-Item -ItemType Directory -Path logs,plugins,temp,dags,tests,data, -Force"; \
        echo "Note: skipped chmod on Windows-like shell"; \
    else \
        # Unix-like: try without sudo first, fallback to sudo if needed \
        mkdir -p logs plugins temp dags tests data ; \
        if [ -w logs ] || [ "$$EUID" -eq 0 ]; then \
            chmod -R 0775 logs plugins temp dags tests data  || true; \
        else \
            if command -v sudo >/dev/null 2>&1; then \
                echo "Using sudo to set permissions"; \
                sudo chmod -R 0775 logs plugins temp dags tests data  || true; \
            else \
                echo "Warning: cannot set permissions (no write access and sudo not available)."; \
            fi \
        fi \
    fi

setup-conn:
	docker exec scheduler python /opt/airflow/setup_conn.py

do-sleep:
	sleep 30

up: perms docker-spin-up do-sleep setup-conn

down:
	docker compose down

restart: down up

sh:
	docker exec -ti webserver bash

####################################################################################################################
# Testing, auto formatting, type checks, & Lint checks
pytest:
	docker exec webserver pytest -p no:warnings -v /opt/airflow/tests

format:
	docker exec webserver python -m black -S --line-length 79 .

isort:
	docker exec webserver isort .

type:
	docker exec webserver mypy --ignore-missing-imports /opt/airflow

lint: 
	docker exec webserver flake8 /opt/airflow/dags

ci: isort format type lint pytest

