FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY web/backend/requirements.txt web/backend/requirements-postgres.txt web/backend/requirements-ai.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements-ai.txt
COPY web/backend ./backend
COPY app ./app
COPY web/frontend/dist ./frontend/dist
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
