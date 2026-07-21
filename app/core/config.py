import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "Custom Chatbot"
VERSION = "1.0.0"
SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "")
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "5000"))
