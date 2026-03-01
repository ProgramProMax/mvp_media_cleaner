FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# ensure package directory is on Python path
ENV PYTHONPATH=/app

# default command, overridden by compose when migrations need running
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]