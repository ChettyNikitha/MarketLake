from fastapi import Request
from fastapi.templating import Jinja2Templates
import requests

from authentication import sign_request, BASE_URL

# Load HTML templates from the templates folder
templates = Jinja2Templates(directory="templates")


# Fetch and display IPL cricket events from the Kalshi API
def get_cricket_events_ui(request: Request):
    try:
        # Create signed headers for the milestones endpoint
        headers = sign_request("GET", "/trade-api/v2/milestones")

        # Fetch IPL-related cricket events
        response = requests.get(
            f"{BASE_URL}/trade-api/v2/milestones",
            headers=headers,
            params={
                "limit": 50,
                "category": "Sports",
                "competition": "IPL" ,
                
            }
        )

        if response.status_code == 200:
            # Convert API response into Python dictionary
            data = response.json()
            milestones = data.get("milestones", [])

            # Store only the fields needed by the UI
            simplified = []

            for item in milestones:
                title = item.get("title")
                related_event_tickers = item.get("related_event_tickers", [])
                start_date = item.get("start_date")

                # Use the first event ticker if available
                event_ticker = related_event_tickers[0] if related_event_tickers else None

                # Skip incomplete or older events
                if not event_ticker:
                    continue

                if not start_date:
                    continue

                if start_date < "2026-01-01":
                    continue

                simplified.append({
                    "title": title,
                    "event_ticker": event_ticker,
                    "start_date": start_date
                })

            # Render the HTML page with the filtered event list
            return templates.TemplateResponse(
                request=request,
                name="cricket_events.html",
                context={
                    "events": simplified
                }
            )

        # Return an error if the API request failed
        return {
            "error": "Failed to fetch cricket events",
            "code": response.status_code
        }

    except Exception as e:
        # Print the full error in the terminal for debugging
        import traceback
        print("FULL ERROR:", traceback.format_exc())

        return {"error": str(e)}