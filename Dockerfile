# Dockerfile

# --- Stage 1: The "Builder" Stage ---
# We align the Python version to 3.11 to perfectly match the distroless base image.
FROM python:3.11-slim-bookworm AS builder

# Set the working directory.
WORKDIR /app

# Set environment variables for Python.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build-time OS dependencies.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy only the requirements file to leverage layer caching.
COPY requirements.txt .

# Upgrade pip and install Python dependencies into an isolated prefix.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix="/install" -r requirements.txt


# --- Stage 2: The "Final" Stage ---
# Use Google's "distroless" image. It is based on Debian 12 and uses Python 3.11.
FROM gcr.io/distroless/python3-debian12

# Set the working directory.
WORKDIR /app

# --- START: DEFINITIVE PATH AND PYTHONPATH FIX ---
# Add the directory for our executables (uvicorn, arq) to the system's PATH.
ENV PATH="/usr/local/bin:${PATH}"
# Add the directory for our Python libraries to the PYTHONPATH.
# This is the crucial fix for the "ModuleNotFoundError".
ENV PYTHONPATH="/usr/local/lib/python3.11/site-packages"
# --- END: DEFINITIVE PATH AND PYTHONPATH FIX ---

# Set standard Python environment variables.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy the installed Python packages from the builder stage.
COPY --from=builder /install /usr/local

# Copy the application source code from the local build context.
COPY . .

# Expose the port the FastAPI server will run on.
EXPOSE 9500

# Define the command to run the application using its absolute path.
CMD ["/usr/local/bin/uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "9500"]