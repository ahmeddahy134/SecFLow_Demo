FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root appuser
RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -s /bin/sh -d /app appuser

# Copy project
COPY . .

# Copy startup script
COPY start.py /app/start.py

# Ensure uploads directory exists and is owned by appuser
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port (Cloud Run uses PORT env var, defaults to 8080)
EXPOSE 8080

# Set PORT environment variable for uvicorn
ENV PORT=8080

# Run the application using Python startup script
# This ensures PORT environment variable is properly read
# Use exec form to ensure proper signal handling
CMD ["python", "-u", "start.py"]

