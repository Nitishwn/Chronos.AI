FROM python:3.10-slim
WORKDIR /app
ENV PYTHONPATH /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8080
CMD ["python", "-m", "app.main"]