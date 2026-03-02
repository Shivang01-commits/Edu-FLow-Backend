from fastapi import FastAPI
from src.routes.routes import router

app = FastAPI()

app.include_router(router=router)

@app.get("/")
async def root():
    return "Backend running successfully!"
