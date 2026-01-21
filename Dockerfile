FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# Copy app
COPY . /app

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# CMD ["gunicorn", "hrms.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
CMD ["sh", "-c", "python manage.py migrate && gunicorn hrms.wsgi:application --bind 0.0.0.0:$PORT --workers 2"]