from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(
    title="Arham's Autonomous Agent API",
    description="Fast API endpoints for the Autonomous Agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://arhamsagent.cc"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class NewsRequest(BaseModel):
    topic: str
    page_size: int = 5

@app.get("/")
def root():
    return {"message": "Arham Autonomous Agent API", "version": "1.0.0"}

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/news/{topic}")
def get_news(topic: str, page_size: int = 5):
    try:
        from news_tool import get_top_news
        result = get_top_news(topic=topic, page_size=page_size)
        return {"topic": topic, "news": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/news")
def post_news(request: NewsRequest):
    try:
        from news_tool import get_top_news
        result = get_top_news(topic=request.topic, page_size=request.page_size)
        return {"topic": request.topic, "news": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
