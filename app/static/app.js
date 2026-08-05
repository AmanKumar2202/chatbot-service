const form = document.querySelector('#chat-form');
const input = document.querySelector('#message');
const messages = document.querySelector('#messages');
const notice = document.querySelector('#notice');
const apiKeyInput = document.querySelector('#api-key');
const connectButton = document.querySelector('#connect');
const userId = localStorage.getItem('chat-user-id') || crypto.randomUUID();
let serviceKey = sessionStorage.getItem('service-key') || '';
const history = [];
localStorage.setItem('chat-user-id', userId);
apiKeyInput.value = serviceKey;

function renderMessage(text, role) {
  const item = document.createElement('article');
  item.className = `message ${role}`;
  item.textContent = text;
  messages.appendChild(item);
  messages.scrollTop = messages.scrollHeight;
  return item;
}

connectButton.addEventListener('click', () => {
  serviceKey = apiKeyInput.value.trim();
  if (!serviceKey) {
    notice.textContent = 'Enter the service key first.';
    return;
  }
  sessionStorage.setItem('service-key', serviceKey);
  notice.textContent = 'Connected. Your next message will use streaming.';
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  if (!serviceKey) {
    notice.textContent = 'Enter the service key and connect first.';
    return;
  }

  renderMessage(message, 'user');
  input.value = '';
  const button = form.querySelector('button');
  button.disabled = true;
  notice.textContent = 'Thinking locally…';
  const assistantItem = renderMessage('', 'assistant');
  let reply = '';

  try {
    const response = await fetch('/api/chatbot/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Service-Key': serviceKey },
      body: JSON.stringify({ message, user_id: userId, history })
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Request failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let metadata = null;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop();
      for (const eventText of events) {
        const dataLine = eventText.split('\n').find(line => line.startsWith('data: '));
        if (!dataLine) continue;
        const eventData = JSON.parse(dataLine.slice(6));
        if (eventData.delta) {
          reply += eventData.delta;
          assistantItem.textContent = reply;
          messages.scrollTop = messages.scrollHeight;
        }
        if (eventData.done) metadata = eventData;
      }
    }
    history.push({ role: 'user', content: message }, { role: 'assistant', content: reply });
    if (history.length > 20) history.splice(0, history.length - 20);
    if (metadata?.tool_call) {
      renderMessage(`Action requested: ${JSON.stringify(metadata.tool_call, null, 2)}`, 'assistant');
    }
    notice.textContent = metadata
      ? `${metadata.agent} · ${metadata.intent} · ${Math.round(metadata.confidence * 100)}% confidence${metadata.sources?.length ? ` · ${metadata.sources.length} source(s)` : ''}`
      : 'Response complete';
  } catch (error) {
    assistantItem.remove();
    notice.textContent = error.message;
  } finally {
    button.disabled = false;
    input.focus();
  }
});

if (serviceKey) notice.textContent = 'Connected with the saved service key.';
