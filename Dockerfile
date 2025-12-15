# Usa una imagen base de Python oficial (versión ligera)
FROM python:3.10-slim
# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Evita que Python genere archivos .pyc y habilita logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copia el archivo de requerimientos primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instala las dependencias necesarias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de la aplicación al contenedor
COPY . .

# Expone el puerto 8080 (Cloud Run usa este por defecto, pero es informativo)
EXPOSE 8080

# ✅ COMANDO CLAVE PARA CLOUD RUN:
# Usamos "sh -c" para que el sistema lea la variable de entorno $PORT.
# Si Cloud Run asigna un puerto (ej. 8080), lo usará. Si no, usará 8080 por defecto.
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"