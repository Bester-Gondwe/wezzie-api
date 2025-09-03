from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.routes.auth.router import router as auth_router
from app.routes.patients.router import router as patients_router
from app.routes.staffs.router import router as staffs_router

app = FastAPI(title="Wezzie API", version="1.0.0")


@app.get("/", include_in_schema=False)
def read_root():
    return RedirectResponse(url="/docs")



api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(patients_router)
api_v1_router.include_router(staffs_router)

app.include_router(api_v1_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
