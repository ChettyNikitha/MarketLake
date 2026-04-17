from fastapi import Request
from fastapi.templating import Jinja2Templates
import requests

from authentication import sign_request, BASE_URL

# Load HTML templates from the templates folder
templates = Jinja2Templates(directory="templates")


# Fetch and display the market details for a selected cricket event
def get_cricket_event_details(request: Request, event_ticker: str):
    try:
        # Create signed headers for the selected event endpoint
        headers = sign_request("GET", f"/trade-api/v2/events/{event_ticker}")

        # Fetch event and market details from Kalshi
        response = requests.get(
            f"{BASE_URL}/trade-api/v2/events/{event_ticker}",
            headers=headers
        )

        if response.status_code == 200:
            # Convert API response into Python dictionary
            data = response.json()

            # Extract event-level details and related markets
            event = data.get("event", {})
            markets = data.get("markets", [])

            # Store only the market fields needed for the UI
            simplified_markets = []

            for market in markets:
                simplified_markets.append({
                    "ticker": market.get("ticker"),
                    "title": market.get("title"),
                    "yes_sub_title": market.get("yes_sub_title"),
                    "no_sub_title": market.get("no_sub_title"),
                    "status": market.get("status")
                })

            # Render the details page with event and market data
            return templates.TemplateResponse(
                request=request,
                name="cricket_event_details.html",
                context={
                    "event_title": event.get("title"),
                    "event_ticker": event.get("event_ticker"),
                    "markets": simplified_markets
                }
            )

        # Return an error if the event request failed
        return {
            "error": "Failed to fetch cricket event details",
            "code": response.status_code,
            "detail": response.text
        }

    except Exception as e:
        # Return the error message if something unexpected happens
        return {"error": str(e)}