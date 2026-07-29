from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.attention.router import router as attention_router
from ai.nudge.router import router as nudge_router


app = FastAPI(title="LumiNudge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://luminudge.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(attention_router)
app.include_router(nudge_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
