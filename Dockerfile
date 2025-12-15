# Usamos Python 3.10 como acordamos para arreglar el error de librerías
FROM python:3.10-slim

# Directorio de trabajo
WORKDIR /app

# Variables de entorno para optimizar Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copiamos requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# Informamos el puerto
EXPOSE 8080

# === COMANDO CRÍTICO ===
# 1. Usamos "sh -c" para leer variables.
# 2. Forzamos --host 0.0.0.0 (¡Vital!).
# 3. Usamos el puerto que nos da Google o 8080 por defecto.
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"