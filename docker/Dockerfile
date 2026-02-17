FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    # fonts-unifont \
    # fonts-liberation \
    # libnss3 \
    # libatk-bridge2.0-0 \
    # libatk1.0-0 \
    # libatspi2.0-0 \
    # libdrm2 \
    # libxkbcommon0 \
    # libxcomposite1 \
    # libxdamage1 \
    # libxfixes3 \
    # libxrandr2 \
    # libgbm1 \
    # libasound2 \
    # libpango-1.0-0 \
    # libcairo2 \
    # libxshmfence1 \
    # libxss1 \
    # libgdk-pixbuf2.0-0 \
    # libgtk-3-0 \
    # libx11-xcb1 \
    # libxcb-dri3-0 \
    # libxext6 \
    # libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
# RUN playwright install chromium

# Note: Essential Playwright dependencies are installed above
# Skipping 'playwright install-deps' due to missing font packages in Debian Trixie
# The manually installed packages above should be sufficient for Chromium to run

# Copy application code
COPY src/ ./src/
COPY pyproject.toml .

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

