# Dockerfile

# --- Stage 1: Base ---
# This common base stage prepares the user and directories.
FROM cgr.dev/chainguard/python:latest-dev AS base
WORKDIR /app
ENV PATH="/home/nonroot/.local/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Switch to root to perform privileged operations
USER root
RUN apk update && apk add build-base python3-dev
RUN mkdir /install && chown -R nonroot:nonroot /app /install
# Switch back to the secure non-root user for all subsequent operations.
USER nonroot

# --- Stage 2: Development & Testing ---
# This stage is specifically for running our tests.
FROM base AS development

# --- START: THE DEFINITIVE FIX ---
# Use the --chown flag to ensure the copied files are owned by the non-root user.
COPY --chown=nonroot:nonroot requirements.in requirements.txt dev-requirements.in dev-requirements.txt ./
# --- END: THE DEFINITIVE FIX ---

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -r dev-requirements.txt

# --- START: THE DEFINITIVE FIX ---
# Also use --chown here for the application source code.
COPY --chown=nonroot:nonroot . .
# --- END: THE DEFINITIVE FIX ---

# --- Stage 3: Production ---
# This is the final, lean image for running the application.
FROM base AS production

# --- START: THE DEFINITIVE FIX ---
COPY --chown=nonroot:nonroot requirements.txt ./
# --- END: THE DEFINITIVE FIX ---

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- START: THE DEFINITIVE FIX ---
COPY --chown=nonroot:nonroot . .
# --- END: THE DEFINITIVE FIX ---

# --- Final Image Selection (Implicit) ---
FROM production
EXPOSE 9500
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "9500"]