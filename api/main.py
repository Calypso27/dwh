"""
Point d'entrée de l'API REST.

Lancement local :
    uvicorn api.main:app --reload

Documentation interactive générée automatiquement :
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import health, auth_router, posts, metrics, behavior

app = FastAPI(
    title="Saint Jean — API d'analyse de communautés sociales",
    description=(
        "API REST générique d'analyse de réseaux sociaux et de recommandation "
        "communautaire, validée sur des datasets publics avant application à "
        "l'Institut Universitaire Saint Jean."
    ),
    version="0.1.0",
)

# Autorise le frontend Angular (servi sur un port différent en dev) à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth_router.router)
app.include_router(posts.router)
app.include_router(metrics.router)
app.include_router(behavior.router)
