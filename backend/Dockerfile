# Python ka lightweight version use karein
FROM python:3.9-slim

# Working directory set karein
WORKDIR /app

# Dependencies install karein
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Saara code copy karein
COPY . .

# Port expose karein
EXPOSE 8080

# Server start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]