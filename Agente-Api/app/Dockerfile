FROM python:3.10-slim

# Crear grupo y usuario docker
RUN groupadd -g 990 docker
RUN useradd -m -g docker appuser

# Establecer usuario root para operaciones iniciales
USER root

# Directorio de trabajo
WORKDIR /app

# Copiar dependencias e instalarlas
COPY dependencias.txt .
RUN pip install --no-cache-dir -r dependencias.txt

# Copiar todo el proyecto al contenedor
COPY . .

# Cambiar permisos del script
RUN chmod +x start.sh

# Establecer PYTHONPATH
ENV PYTHONPATH=/app

# Exponer puerto de FastAPI
EXPOSE 8000

# Cambiar a usuario appuser
USER appuser

# Comando por defecto
CMD ["./start.sh"]
