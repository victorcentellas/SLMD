# Usa una imagen base ligera de Python
FROM python:3.10-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos necesarios al contenedor
COPY dependencias.txt .
COPY Agente.py .

# Instala las dependencias
RUN pip install --no-cache-dir -r dependencias.txt

# Expone el puerto MQTT (opcional si se comunica con otros contenedores)
EXPOSE 1883

ENV BROKER_HOST=localhost
ENV BROKER_PORT=1883

# Ejecuta el script
CMD ["python", "Agente.py"]
