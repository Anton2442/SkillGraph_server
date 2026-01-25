from fastapi import FastAPI
from fastapi.responses import JSONResponse
from authx.exceptions import JWTDecodeError
import uvicorn

from routes.auth import router as auth_router

app = FastAPI()

app.include_router(auth_router)


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