import os

from fastapi import HTTPException, Request


def require_api_key(request: Request):
    secret = os.getenv("SERVER_API_KEY")
    if not secret:
        return
    key = request.headers.get("X-API-Key")
    if key != secret:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
