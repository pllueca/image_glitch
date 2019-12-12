FROM python:3.8.0-slim

RUN apt update && apt install -y ffmpeg g++ curl gcc zlib1g-dev
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

WORKDIR /opt/glitch
COPY . .

ENV FLASK_APP=glitch_app.py
CMD ["python", "glitch_app.py"]
