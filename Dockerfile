FROM python:3.12-slim

COPY lux2influxdb.py .
COPY metrics.py .
COPY requirements.txt .
RUN pip install -r requirements.txt
CMD ["python", "-u", "./lux2influxdb.py"] 
