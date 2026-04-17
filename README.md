

## Kalshi Cricket Market App 

This project is a FastAPI application connected to the Kalshi Demo API.

## Features 
- Home page
- IPL cricket events page
- Event details page with market information
- Signed API authentication
- Docker support

## Project Structure 
main.py
authentication.py
cricket_events.py
cricket_event_details.py
templates/
Dockerfile
requirements.txt

## Run Locally  in Bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

Open:

http://127.0.0.1:8000
http://127.0.0.1:8000/cricket-events-ui

## Run with Docker
docker build -t kalshi-app .
docker run -p 8000:8000 kalshi-app