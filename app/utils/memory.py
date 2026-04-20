user_memory = {}


def get_history(user_id: str):
    return user_memory.get(user_id, [])


def update_history(user_id: str, message: str):
    if user_id not in user_memory:
        user_memory[user_id] = []

    user_memory[user_id].append(message)

    # Keep last 5 messages
    user_memory[user_id] = user_memory[user_id][-5:]