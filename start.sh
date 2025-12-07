#!/bin/bash
# Utilise $PORT si défini, sinon 8000 par défaut
PORT=${PORT:-8000}
uvicorn app.main:app --host 0.0.0.0 --port $PORT
