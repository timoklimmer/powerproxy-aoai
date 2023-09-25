# Build container
FROM docker.io/library/python:3.11-slim-bullseye@sha256:de917502e531b3f6e4a5acef017e9feef392cf3eb76826fd46d6810c70ae9b5e AS build

RUN apt-get update \
  && apt-get install --yes gcc python3-dev \
  && python3 -m pip install --upgrade pip setuptools wheel

RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH

COPY requirements.txt .
RUN python3 -m pip install --requirement requirements.txt

# Output container
FROM docker.io/library/python:3.11-slim-bullseye@sha256:de917502e531b3f6e4a5acef017e9feef392cf3eb76826fd46d6810c70ae9b5e

# Tell the host we are running on port 8000
# Note: We intentionally run on a port >= 1024 here because lower ports needed special treatment.
EXPOSE 8000

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN useradd -m appuser \
  && mkdir /app \
  && chown -R appuser:appuser /app

USER appuser

COPY --from=build /venv /venv
ENV PATH=/venv/bin:$PATH

COPY --chown=appuser:appuser /app /app

# Note about headers:
# - We do need those related to proxy (param named "proxy-headers"), in the case the app is ran in a container behind a reverse proxy, like Traefik, Nginx, etc.
# - We do need those related to date (param named "date-header"), as we want to be able to see the date of the request in the monitoring, and the customer able to calculate the latency plus cache the response.
# - We do not need those related to server (param named "server-header"), as we do not want to expose the fact that we are using FastAPI or Uvicorn, this is a security measure.
CMD ["bash", "-c", "WEB_CONCURRENCY=4 cd /app && uvicorn powerproxy:app --host 0.0.0.0 --port 8000 --proxy-headers --no-server-header --timeout-keep-alive 120 --timeout-graceful-shutdown 120"]
