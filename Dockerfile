# Use Python 3.11 slim image
FROM python:3.11-slim

# Install libusb for NFC reader support and usbutils for debugging
RUN apt-get update && \
    apt-get install -y libusb-1.0-0 libusb-1.0-0-dev usbutils && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

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
