# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies for USB/NFC reader support
# libusb, pcscd (PC/SC daemon for smart card readers), and related tools
RUN apt-get update && \
    apt-get install -y \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    pcscd \
    pcsc-tools \
    libnfc6 \
    libnfc-dev \
    udev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and resources
COPY app.py .
COPY diagnostics.py .
COPY data_viewer.py .
COPY init_card_reader.sh .
COPY static/ ./static/
COPY templates/ ./templates/

# Make scripts executable
RUN chmod +x init_card_reader.sh

# Expose port
EXPOSE 5000

# Create startup script that initializes card reader and starts Flask
RUN echo '#!/bin/bash\n\
echo "Starting OITELU Server..."\n\
echo ""\n\
# Start PC/SC daemon in background if available\n\
if command -v pcscd &> /dev/null; then\n\
    echo "Starting PC/SC daemon..."\n\
    pcscd --debug --apdu 2>&1 | head -n 5 &\n\
    sleep 2\n\
fi\n\
echo ""\n\
# Start Flask application\n\
python app.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# Run startup script
CMD ["/app/start.sh"]
