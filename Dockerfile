# Usamos una imagen ligera oficial de Python
FROM python:3.11-slim

# Evita que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE=1
# Evita que Python guarde en buffer las salidas de consola
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# CORRECCIÓN: Agregamos pkg-config y libcairo2-dev para que pycairo pueda compilarse
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    pkg-config \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiamos el archivo respetando el nombre exacto de tus requerimientos
COPY requeriments.txt /app/

# Aseguramos tener pip actualizado e instalamos dependencias + gunicorn
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requeriments.txt \
    && pip install --no-cache-dir gunicorn

# Copiamos todo el código fuente del proyecto
COPY . /app/

# Expone el puerto interno donde correrá Gunicorn
EXPOSE 8000

# Comando por defecto: Recolecta estáticos, ejecuta migraciones y levanta el servidor
CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn digital_payroll_system.wsgi:application --bind 0.0.0.0:8000"]