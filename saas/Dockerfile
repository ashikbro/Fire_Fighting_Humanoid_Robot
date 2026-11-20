FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fireops ./fireops
COPY robot_client.py .
ENV FIREOPS_DB=/data/fireops.db
VOLUME ["/data"]
EXPOSE 8000
CMD ["uvicorn", "fireops.main:app", "--host", "0.0.0.0", "--port", "8000"]
