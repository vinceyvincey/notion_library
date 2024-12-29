# Use the official Python image from the Docker Hub
FROM python:3.13.0-slim

# Set working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . .

# Install uv for faster dependency installation
RUN pip install uv

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies using uv
RUN uv sync

# Make port 8000 available
EXPOSE 8000

# Run the FastAPI app with Hypercorn
CMD hypercorn main:app --bind 0.0.0.0:${PORT:-8000} 