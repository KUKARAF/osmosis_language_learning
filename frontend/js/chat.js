import { apiFetch, apiGet, apiPost, apiDelete } from './api.js';
import { initCat } from './cat.js';

let conversationId = null;
let devMode = false;
let abortController = null;
let srsWordsSet = new Set(); // lowercase word fronts from SRS

async function loadSrsWords() {
  try {
    const words = await apiGet('/srs/words');
    srsWordsSet = new Set(words.map(w => w.front.toLowerCase()));
  } catch {
    // non-critical — highlighting degrades gracefully
  }
}

function highlightSrsWords(el) {
  if (!srsWordsSet.size) return;
  const text = el.textContent;
  const wordPattern = /[\p{L}\p{N}]+/gu;
  const fragment = document.createDocumentFragment();
  let lastIndex = 0;
  let match;
  let hasHighlight = false;
  while ((match = wordPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      fragment.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
    }
    const word = match[0];
    if (srsWordsSet.has(word.toLowerCase())) {
      const span = document.createElement('span');
      span.className = 'srs-word';
      span.textContent = word;
      fragment.appendChild(span);
      hasHighlight = true;
    } else {
      fragment.appendChild(document.createTextNode(word));
    }
    lastIndex = match.index + word.length;
  }
  if (lastIndex < text.length) {
    fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
  }
  if (hasHighlight) {
    el.textContent = '';
    el.appendChild(fragment);
  }
}

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
    const el = appendMessage(msg.role, msg.content || '');
    if (msg.role === 'user') highlightSrsWords(el);
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

  const userEl = appendMessage('user', text);
  highlightSrsWords(userEl);
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
            if (data.name === 'rate_word' && data.arguments?.rating < 4) {
              const word = data.arguments.word || '';
              appendMessage('correction', `btw, that's not how you write/use "${word}"`);
            }
            break;
          case 'tool_result':
            if (data.result?.action === 'capture_homework_photo') {
              renderHomeworkCapture(data.result);
            }
            break;
          case 'done':
            loadSrsWords();
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

function renderHomeworkCapture(toolResult) {
  const { subject, message, upload_url } = toolResult;

  const bubble = document.createElement('div');
  bubble.className = 'message message-assistant';

  const msgText = document.createElement('p');
  msgText.textContent = message;
  bubble.appendChild(msgText);

  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = 'image/*';
  fileInput.capture = 'environment';
  fileInput.style.display = 'none';

  const btn = document.createElement('button');
  btn.textContent = '📷 Photograph homework';
  btn.className = 'btn btn-primary';
  btn.style.marginTop = '0.5rem';
  btn.onclick = () => fileInput.click();

  const status = document.createElement('p');
  status.style.marginTop = '0.5rem';
  status.style.fontStyle = 'italic';

  fileInput.onchange = async () => {
    const file = fileInput.files[0];
    if (!file) return;

    btn.disabled = true;
    status.textContent = 'Analyzing your homework…';

    try {
      const me = await apiGet('/users/me');
      const language = me.target_language || 'English';

      const id = await ensureConversation();
      const form = new FormData();
      form.append('subject', subject);
      form.append('language', language);
      form.append('conversation_id', id);
      form.append('photo', file);

      const result = await apiFetch(upload_url, { method: 'POST', body: form, raw: false });

      status.textContent = '';
      appendMessage(
        'assistant',
        `I've set up ${result.vocab_count} vocabulary word${result.vocab_count !== 1 ? 's' : ''} and ` +
        `${result.grammar_count} grammar pattern${result.grammar_count !== 1 ? 's' : ''} from your homework. ` +
        `Chat with me and I'll let you know when you're ready!`
      );
    } catch (err) {
      status.textContent = `Upload failed: ${err.message}`;
      btn.disabled = false;
    }
  };

  bubble.appendChild(btn);
  bubble.appendChild(fileInput);
  bubble.appendChild(status);

  const container = document.getElementById('chat-messages');
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

export async function initChat() {
  await initCat();
  await loadSrsWords();

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

  // Show clear-memory button in dev mode
  const clearBtn = document.getElementById('clear-memory-btn');
  if (devMode && clearBtn) {
    clearBtn.hidden = false;
    clearBtn.onclick = async () => {
      if (!conversationId) return;
      await apiDelete(`/chat/conversations/${conversationId}`);
      conversationId = null;
      document.getElementById('chat-messages').innerHTML = '';
      await ensureConversation();
    };
  }
}

export function setDevMode(enabled) {
  devMode = enabled;
}
