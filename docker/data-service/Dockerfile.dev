FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY run.py .

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=src/web/__init__.py
ENV FLASK_ENV=development

# Run the application
CMD ["python", "run.py"] 