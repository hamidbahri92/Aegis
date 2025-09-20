# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY . /app
# Install core deps; Torch is optional and heavy, so not installed by default.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .
CMD ["python", "main.py"]
