FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LIFELINK_DATABASE=/data/login_auth.db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000
# Schema is ensured at runtime start so it lands on the persistent disk,
# not in an image layer that a fresh volume mount would hide.
CMD ["sh", "-c", "python database/bootstrap.py && gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 2 wsgi:app"]
