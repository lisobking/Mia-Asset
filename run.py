import os
import sys
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"[run.py] Starting server on 0.0.0.0:{port} (PORT env={os.environ.get('PORT', 'NOT SET')})", flush=True)
    sys.stdout.flush()
    uvicorn.run("api.main:app", host="0.0.0.0", port=port)
