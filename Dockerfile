# Use a Python 3.11 base image
FROM python:3.11

# Install espeak-ng
RUN apt-get update && apt-get install -y espeak-ng

# Set the working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Start the app with gunicorn
CMD ["gunicorn", "main:app"]
