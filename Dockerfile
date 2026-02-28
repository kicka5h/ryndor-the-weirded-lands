FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ ./app/

# Streamlit config
RUN mkdir -p /root/.streamlit
RUN echo '\
[server]\n\
port = 8501\n\
address = "0.0.0.0"\n\
headless = true\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
\n\
[theme]\n\
base = "dark"\n\
backgroundColor = "#040010"\n\
secondaryBackgroundColor = "#080118"\n\
textColor = "#e2d9f3"\n\
primaryColor = "#7c3aed"\n\
' > /root/.streamlit/config.toml

EXPOSE 8501

CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
