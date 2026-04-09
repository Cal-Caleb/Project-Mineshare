"""API server entrypoint."""

import uvicorn

from core.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
