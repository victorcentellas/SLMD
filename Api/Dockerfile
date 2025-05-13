FROM python:3.10-slim

# Crear el grupo docker (esto es solo en el contenedor)
RUN groupadd -g 990 docker

# Crear un usuario y agregarlo al grupo docker (esto es solo en el contenedor)
RUN useradd -m -g docker appuser

# Establecer el usuario como root para las operaciones iniciales
USER root

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar las dependencias e instalar las dependencias de Python
COPY dependencias.txt .
RUN pip install --no-cache-dir -r dependencias.txt

# Copiar los archivos necesarios
COPY api.py .
COPY start.sh .

# Cambiar permisos de start.sh
RUN chmod +x start.sh

# Establecer el usuario de nuevo a appuser para la ejecución
USER appuser

EXPOSE 8000

# Definir el comando por defecto
CMD ["./start.sh"]
