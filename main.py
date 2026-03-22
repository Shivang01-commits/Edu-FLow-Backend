import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.db.main import init_db

from src.routes.new_book_routes import router as new_book_router
from src.routes.auth_routes import router as auth_router
from src.routes.sudo_admin_routes import router as sudo_admin_router
from src.routes.admin_routes import router as admin_router
from src.routes.teacher_routes import router as teacher_router
from src.routes.student_routes import router as student_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server starting...")
    try:
        init_db()
        print("DB initialized")
    except Exception as e:
        print("DB init failed:", e)
    yield
    print("Server shutting down...")


app = FastAPI(
    lifespan=lifespan,
    title="Padhai App",
    version="1.0.0",
    description="Backend API for Padhai — school content management platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(sudo_admin_router)
app.include_router(new_book_router)
app.include_router(admin_router)
app.include_router(teacher_router)
app.include_router(student_router)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


@app.get("/", tags=["Health"])
def root():
    return {"message": "Backend running successfully"}
