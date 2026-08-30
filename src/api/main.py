from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes_catalog import router as catalog_router
from src.api.routes_evaluation_lab import router as evaluation_lab_router
from src.api.routes_genai import router as genai_router
from src.api.routes_generate import router as generate_router
from src.api.routes_loop import router as loop_router
from src.api.routes_portfolio import router as portfolio_router
from src.api.routes_score import router as score_router


app = FastAPI(
    title="GenAI Payment Fraud Red-Team/Blue-Team API",
    description="API for attack catalog validation, synthetic fraud generation, detection, scoring, and evaluation.",
    version="0.1.0",
)

# The browser prototype is served separately during local development.  Keep
# the permitted origins explicit so production can replace this list with its
# own deployed UI origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    # Vite uses the next available port when 5173 is busy.  This keeps local
    # development usable without opening CORS to non-local origins.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": "0.1.0",
    }


app.include_router(catalog_router)
app.include_router(evaluation_lab_router)
app.include_router(generate_router)
app.include_router(score_router)
app.include_router(loop_router)
app.include_router(genai_router)
app.include_router(portfolio_router)
