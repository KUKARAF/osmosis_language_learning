import { apiFetch, apiGet, apiPost } from './api.js';
import { initCat } from './cat.js';

let conversationId = null;
let abortController = null;

export function teardownChat() {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
}

function appendMessage(role, content) {
  const el = document.createElement('div');
  el.className = `message message-${role}`;
  el.textContent = content;
  const container = document.getElementById('chat-messages');
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  return el;
}

function renderHistory(messages) {
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';
  for (const msg of messages) {
    if (msg.role === 'system') continue;
    appendMessage(msg.role, msg.content || '');
  }
}

async function ensureConversation() {
  if (conversationId) return conversationId;

  const convos = await apiGet('/chat/conversations');
  if (convos.length > 0) {
    conversationId = convos[0].id;
  } else {
    const created = await apiPost('/chat/conversations', {});
    conversationId = created.id;
  }
  return conversationId;
}

function parseSSE(chunk) {
  const events = [];
  const blocks = chunk.split('\n\n');
  for (const block of blocks) {
    if (!block.trim()) continue;
    const lines = block.split('\n');
    let event = 'message';
    let data = '';
    for (const line of lines) {
      if (line.startsWith('event:')) {
        event = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        data = line.slice(5).trim();
      }
    }
    if (data) {
      try {
        events.push({ event, data: JSON.parse(data) });
      } catch {
        events.push({ event, data: { content: data } });
      }
    }
  }
  return events;
}

async function sendMessage(text) {
  if (!text.trim()) return;

  appendMessage('user', text);
  document.getElementById('chat-input').value = '';

  const id = await ensureConversation();

  const assistantEl = appendMessage('assistant', '');
  assistantEl.classList.add('message-streaming');

  teardownChat();
  abortController = new AbortController();

  try {
    const res = await apiFetch(`/chat/conversations/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content: text }),
      raw: true,
      signal: abortController.signal,
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const lastDoubleNewline = buffer.lastIndexOf('\n\n');
      if (lastDoubleNewline === -1) continue;

      const complete = buffer.slice(0, lastDoubleNewline + 2);
      buffer = buffer.slice(lastDoubleNewline + 2);

      const events = parseSSE(complete);
      for (const { event, data } of events) {
        switch (event) {
          case 'token':
            assistantEl.textContent += data.content || '';
            document.getElementById('chat-messages').scrollTop =
              document.getElementById('chat-messages').scrollHeight;
            break;
          case 'tool_call':
            appendMessage('tool', `⚙ ${data.name || 'tool call'}`);
            break;
          case 'tool_result':
            break;
          case 'done':
            break;
          case 'error':
            assistantEl.textContent += `\n[error: ${data.detail || data.content || 'unknown'}]`;
            break;
        }
      }
    }

    // Process any remaining buffer
    if (buffer.trim()) {
      const events = parseSSE(buffer);
      for (const { event, data } of events) {
        if (event === 'token') {
          assistantEl.textContent += data.content || '';
        }
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      assistantEl.textContent += `\n[error: ${err.message}]`;
    }
  } finally {
    assistantEl.classList.remove('message-streaming');
    abortController = null;
  }
}

export async function initChat() {
  await initCat();

  const id = await ensureConversation();
  try {
    const messages = await apiGet(`/chat/conversations/${id}/messages`);
    renderHistory(messages);
  } catch {
    // Fresh conversation, no history
  }

  const form = document.getElementById('chat-form');
  form.onsubmit = (e) => {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    sendMessage(input.value);
  };
}
