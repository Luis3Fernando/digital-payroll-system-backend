FROM python:3.11-slim

ENV PYTHONTONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    pkg-config \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requeriments.txt /app/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requeriments.txt \
    && pip install --no-cache-dir gunicorn

COPY . /app/

WORKDIR /app/digital_payroll_system

EXPOSE 8000

CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn digital_payroll_system.wsgi:application --bind 0.0.0.0:8000"]