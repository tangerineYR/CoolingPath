FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN python -m pip install --no-cache-dir -e .
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.headless=true"]
