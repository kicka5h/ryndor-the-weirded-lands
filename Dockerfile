FROM python:3.11-slim@sha256:d6e4d224f70f9e0172a06a3a2eba2f768eb146811a349278b38fff3a36463b47

WORKDIR /app

# Upgrade system packages
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ ./app/

# Streamlit config — no port here; port is set at runtime via $PORT
RUN mkdir -p /root/.streamlit
RUN echo '\
[server]\n\
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

# PORT defaults to 8501 locally; Cloud Run overrides it with 8080
EXPOSE 8080

CMD ["sh", "-c", "streamlit run app/app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
