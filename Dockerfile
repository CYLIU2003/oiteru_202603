# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and resources
COPY app.py .
COPY static/ ./static/
COPY templates/ ./templates/

# Expose port
EXPOSE 5000

# Run Flask application
CMD ["python", "app.py"]
