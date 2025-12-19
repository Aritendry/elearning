FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# 1. Installer numpy d'abord
RUN pip install --no-cache-dir --default-timeout=100 numpy==1.26.4

# 2. Installer bytez 3.0.1 avec toutes ses dépendances
RUN pip install --no-cache-dir --default-timeout=100 "bytez==3.0.1"

# 3. Installer le reste
RUN pip install --no-cache-dir --default-timeout=100 \
    Django==5.2.8 \
    psycopg2-binary==2.9.9 \
    Pillow==10.3.0 \
    pandas==2.2.3 \
    requests==2.32.3 \
    opencv-python-headless==4.9.0.80

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]