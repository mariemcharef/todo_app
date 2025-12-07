from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app import routers
app = FastAPI()

origins = [
    "*"
]

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers.user.router)
app.include_router(routers.auth.router)
app.include_router(routers.task.router)




@app.get("/")
async def read_root():
    return {"Hello": "World"}
