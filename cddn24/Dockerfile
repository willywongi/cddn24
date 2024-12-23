# Install and run the backend server
FROM python:3.12-bookworm AS base

# Install additional locales
RUN apt-get update && apt-get install -y locales
# Set locale to it_IT
RUN localedef -i it_IT -c -f UTF-8 -A /usr/share/locale/locale.alias it_IT.UTF-8
ENV LANG it_IT.utf8

FROM base AS python-env

RUN apt-get install -y ffmpeg --no-install-recommends

WORKDIR /cddn24

ENV \
    # This prevents Python from writing out pyc files \
    PYTHONDONTWRITEBYTECODE=1 \
    # This keeps Python from buffering stdin/stdout \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv

RUN set -ex \
    && python3 -m venv $VIRTUAL_ENV \
    && $VIRTUAL_ENV/bin/pip install -U setuptools wheel pip uv

# Install Python packages
COPY requirements.txt .

RUN set -ex \
    && $VIRTUAL_ENV/bin/uv pip install -r requirements.txt \
    && rm -rf /root/.cache/

FROM python-env AS backend

# Inject code version in container
ARG GIT_SHA
# Enable venv
ENV PATH="/opt/venv/bin:$PATH"
# Include git SHA as code version from build arg
ENV CODE_VERSION=${GIT_SHA}
# Tell Docker what port we're exposing
EXPOSE $BACKEND_CONTAINER_PORT
# Copy application files
COPY . .
# Set permission for entrypoint script
RUN ["chmod", "a+x", "run.sh"]

ENTRYPOINT ["/cddn24/run.sh"]

FROM python-env AS worker

# Inject code version in container
ARG GIT_SHA
# Enable venv
ENV PATH="/opt/venv/bin:$PATH"
# Include git SHA as code version from build arg
ENV CODE_VERSION=${GIT_SHA}
# Enable the PYTHONSTARTUP file
ENV PYTHONSTARTUP=/cddn24/.pythonrc.py
# Copy application files
COPY . .

ENTRYPOINT ["python", "manage.py"]
