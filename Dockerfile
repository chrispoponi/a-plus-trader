FROM python:3.9-slim

WORKDIR /app

# Install system deps (if needed for ta-lib later, add here)
# RUN apt-get update && apt-get install -y gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port (Render sets $PORT env var, usually 10000, or we default 8000)
EXPOSE 8000

# Command to run the app
CMD ["uvicorn", "executor_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
