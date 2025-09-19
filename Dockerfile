# Dockerfile

# --- Stage 1: The "Builder" Stage ---
FROM python:3.11-slim-bookworm AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# --- START: MODIFIED DEPENDENCY INSTALLATION ---
# Copy BOTH requirements files.
COPY requirements.in requirements.txt dev-requirements.in dev-requirements.txt ./

# Install BOTH production and development dependencies in this temporary stage.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix="/install" -r requirements.txt -r dev-requirements.txt
# --- END: MODIFIED DEPENDENCY INSTALLATION ---


# --- Stage 2: The "Final" Stage ---
FROM gcr.io/distroless/python3-debian12
WORKDIR /app
ENV PATH="/usr/local/bin:${PATH}"
ENV PYTHONPATH="/usr/local/lib/python3.11/site-packages"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# --- START: CRITICAL SECURITY IMPROVEMENT ---
# Copy ONLY the production dependencies from the builder stage.
# The dev tools (pip-tools, debugpy) are NOT included in the final image.
COPY --from=builder /install /usr/local
# --- END: CRITICAL SECURITY IMPROVEMENT ---
COPY . .
EXPOSE 9500
CMD ["/usr/local/bin/uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "9500"]