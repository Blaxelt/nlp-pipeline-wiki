import logging
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s - %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import articles
from app.api.routes import wikipedia_urls
from contextlib import asynccontextmanager
from app.core.wikipedia_index import load_all
from app.core import article_store

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_all()
    article_store.load_latest()
    yield

app = FastAPI(lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router)
app.include_router(wikipedia_urls.router)