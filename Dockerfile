FROM python:3.9-slim

WORKDIR /app

# Instalacja zależności z kompatybilnymi wersjami
RUN pip install --upgrade pip && \
    pip install pyspark==3.4.1 delta-spark==2.4.0 kafka-python

CMD ["python", "--version"]