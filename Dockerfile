FROM python:3.11-slim

# tell the host we are running on port 8000
# note: we intentionally run on a port >= 1024 here because lower ports needed special treatment
EXPOSE 8000

# keep Python from generating .pyc files
# note: those files won't be needed in a container where a process is run only once.
ENV PYTHONDONTWRITEBYTECODE=1

# turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# set workdir and copy app to image
WORKDIR /app
COPY ./app /app

# create a non-root user with an explicit UID and adds permission to access the /app folder.
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app && mkdir /logs && chown appuser /logs
USER appuser

# define the entry point
ENTRYPOINT uvicorn powerproxy:app \
    --host="0.0.0.0" \
    --port=8000 \
    --log-level warning \
    --no-proxy-headers \
    --no-server-header \
    --no-date-header \
    --timeout-keep-alive 120 \
    --timeout-graceful-shutdown 120 \
    --workers 4
