FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway sets PORT env var
ENV PORT=8000
EXPOSE 8000

# Run the application - use shell form to expand $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
