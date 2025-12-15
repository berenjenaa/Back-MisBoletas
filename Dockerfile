# 1. Usamos Python 3.10
FROM python:3.10-slim

# 2. Directorio de trabajo
WORKDIR /app

# 3. Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# === PARTE NUEVA Y CRÍTICA ===
# Instalamos "libmagic1" que es necesario para detectar tipos de archivos
# Usamos apt-get porque es una imagen basada en Debian
RUN apt-get update && \
    apt-get install -y libmagic1 && \
    rm -rf /var/lib/apt/lists/*
# ==============================

# 4. Copiamos e instalamos dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos el resto del código
COPY . .

# 6. Exponemos el puerto
EXPOSE 8080

# 7. Comando de arranque
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"