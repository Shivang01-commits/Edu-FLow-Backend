from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.db.main import init_db
from src.routes.chapter_routes import router
from src.routes.auth_routes import auth_router
import logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server starting...")
    init_db()
    yield
    print("Server shutting down...")


app = FastAPI(lifespan=lifespan)

app.include_router(router)
app.include_router(auth_router)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)


@app.get("/")
def root():
    return {"message": "Backend running successfully"}
