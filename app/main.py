from fastapi import FastAPI
from app.routes import chatbot

app = FastAPI(title="Custom Chatbot API 🚀")

# Register routes
app.include_router(chatbot.router, prefix="/api/chatbot")


@app.get("/")
def root():
    return {"message": "Chatbot Service Running 🚀"}