# importing fastapi tool from fastapi packages to create app engine, request used to pass browser request to html pages
from fastapi import FastAPI, Request
# importing jinja2 to render html files (without this api retunrs json format )
from fastapi.templating import Jinja2Templates
# importing functions 
from cricket_events import get_cricket_events_ui
from cricket_event_details import get_cricket_event_details
# creating web app engine
app = FastAPI()
# looks for templates in the folder 
templates = Jinja2Templates(directory="templates")

# creating end point , home func to return home page when endpoint is clicked / requested
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html"
    )
# endpoints for eventlist & details if called then the function executes 
@app.get("/cricket-events-ui")
def cricket_events_page(request: Request):
    return get_cricket_events_ui(request)
# event ticker is parameter , like dynamic url parameter takesfrom the selected event , pasing request & parameter to get details
@app.get("/cricket-event-details/{event_ticker}")
def cricket_event_page(request: Request, event_ticker: str):
    return get_cricket_event_details(request, event_ticker)