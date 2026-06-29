FROM python:3.12-slim

WORKDIR /app

COPY sdk/ sdk/
COPY backend/ backend/

RUN pip install --no-cache-dir -e ./sdk -e ./backend

EXPOSE 8420

CMD ["python", "-m", "flight_recorder_backend"]
