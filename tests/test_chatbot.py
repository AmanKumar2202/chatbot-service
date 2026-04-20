import requests

url = "http://localhost:8000/api/chatbot/respond"

data = {
    "message": "hello",
    "user_id": "user123",
    "history": []
}

response = requests.post(url, json=data)

print(response.json())