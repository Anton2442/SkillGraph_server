from fastapi import FastAPI
from fastapi.responses import JSONResponse
from authx.exceptions import JWTDecodeError
import uvicorn

from routes.auth import router as auth_router
from routes.directions import router as directions_router
from routes.graphs import router as graphs_router
from routes.skills import router as skills_router

app = FastAPI(
    docs_url=None,
    redoc_url=None
)

app.include_router(auth_router)
app.include_router(directions_router)
app.include_router(graphs_router)
app.include_router(skills_router)


@app.exception_handler(JWTDecodeError)
async def expired_token_handler(request, exc):
    if "expired" in str(exc).lower():
        return JSONResponse(
            status_code=401,
            content={"detail": "Token expired"}
        )

    return JSONResponse(
        status_code=401,
        content={"detail": "Invalid token"}
    )


if __name__ == "__main__":
    uvicorn.run(app="main:app", reload=True)