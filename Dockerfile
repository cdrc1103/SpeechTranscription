FROM python:3.9-slim

#install all libraries for app
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# update; 8501 is standard for streamlit
EXPOSE 8501
