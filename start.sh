#!/bin/bash
# Start the FastAPI app on the port Render provides
uvicorn app.main:app --host 0.0.0.0 --port $PORT
