FROM python:3.11-slim

WORKDIR /app

# Copy requirements first so dependency installation is cached separately
# from application code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY etl/ ./etl/
COPY db/ ./db/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
