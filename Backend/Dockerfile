# Сборка из корня репозитория: docker build -f Backend/Dockerfile .

# ---- этап 1: ставим зависимости в виртуальное окружение ----
FROM python:3.11-slim-bookworm AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY Backend/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# ---- этап 2: лёгкий образ без инструментов сборки, запуск не от root ----
FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"
RUN groupadd --system app && useradd --system --gid app --home-dir /srv app
COPY --from=builder /opt/venv /opt/venv
WORKDIR /srv/Backend
COPY --chown=app:app Backend/ /srv/Backend/
COPY --chown=app:app Agent/ /srv/Agent/
USER app

EXPOSE 8080
# Команда по умолчанию: веб-часть (API и мини-апп). Бот запускается отдельной командой в docker-compose.yml.
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
