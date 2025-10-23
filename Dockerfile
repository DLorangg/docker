# Use the exact PyTorch image you know works from your current pod
FROM runpod/pytorch:1.0.1-cu1281-torch280-ubuntu2404

# Set the working directory
WORKDIR /workspace

# Install system dependencies (ensure ffmpeg is present) and clean up
# Even though the base might have it, being explicit is safer.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker cache efficiency
COPY requirements.txt .

# Install Python dependencies
# Since the base image already has PyTorch, we install the rest
RUN pip install -r requirements.txt

# Copy the rest of your application code
COPY . .

# Define the default command to run when the container starts
CMD ["python3", "handler.py"]