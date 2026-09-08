from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.routers import analytics, events, health, markets
from app import auth, web

app = FastAPI(title="Kalshi-MarketLake")

app.add_middleware(SessionMiddleware, secret_key=get_settings().session_secret_key, same_site="lax")

app.include_router(auth.router)
app.include_router(web.router)
app.include_router(health.router)
app.include_router(events.router)
app.include_router(markets.router)
app.include_router(analytics.router)
