web: gunicorn -k uvicorn.workers.UvicornWorker app.main:app --workers 3 --timeout 120
release: alembic upgrade head
