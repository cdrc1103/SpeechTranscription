FROM python:3.9-slim

# Create directory to store source code
WORKDIR /app

# Copy repo content
COPY . /app

# install all libraries for app
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# update; 8501 is standard for streamlit
EXPOSE 80

# check if port is reachable
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# set container entry point
ENTRYPOINT ["streamlit", "run", "src/main.py", "--server.port=80", "--server.address=0.0.0.0"]
