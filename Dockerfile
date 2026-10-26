# Image de production : Python 3.12, utilisateur non root, fichiers statiques collectés au build.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# collectstatic ne lit ni la base ni de vrai secret : ces valeurs ne servent qu'à cette étape.
RUN SECRET_KEY=collectstatic-uniquement ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --no-input

RUN useradd --create-home --uid 1000 skillforge \
    && mkdir -p /app/media \
    && chown skillforge /app/media
USER skillforge

EXPOSE 8000
ENTRYPOINT ["./docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
