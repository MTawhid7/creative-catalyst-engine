# Dockerfile

# --- Stage 1: Base ---
FROM cgr.dev/chainguard/python:latest-dev AS base
WORKDIR /app
ENV PATH="/home/nonroot/.local/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER root
RUN apk update && apk add build-base python3-dev
RUN mkdir /install && chown -R nonroot:nonroot /app /install
USER nonroot

# --- Stage 2: Development & Testing ---
FROM base AS development
COPY --chown=nonroot:nonroot requirements.in requirements.txt dev-requirements.in dev-requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -r dev-requirements.txt
COPY --chown=nonroot:nonroot . .

# --- Stage 3: Production ---
FROM base AS production
COPY --chown=nonroot:nonroot requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
COPY --chown=nonroot:nonroot . .

# --- Final Image Selection ---
FROM production
EXPOSE 9500
CMD ["-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "9500"]
