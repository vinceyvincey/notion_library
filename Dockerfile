# Use the official Python image from the Docker Hub
FROM python:3.13.0-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run the FastAPI app with Hypercorn on the specified port, defaulting to 8000
CMD hypercorn main:app --bind 0.0.0.0:${PORT:-8000} 