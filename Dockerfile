# Use a Python 3.11 base image
FROM python:3.11

# Install dependencies (ffmpeg + espeak-ng)
RUN apt-get update && apt-get install -y espeak-ng ffmpeg && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port (needed for Render)
EXPOSE 8000

# Start the app with Gunicorn (optimized for WebSockets)
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8000", "main:app"]

