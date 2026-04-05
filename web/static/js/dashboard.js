/* Jarvis AI - Dashboard JavaScript */

function updateStatus() {
  fetch('/api/status')
    .then(r => r.json())
    .then(data => {
      const cpu = data.cpu_percent ?? '--';
      const ram = data.ram_percent ?? '--';
      const disk = data.disk_percent ?? '--';
      document.getElementById('cpu-val').textContent = cpu + '%';
      document.getElementById('ram-val').textContent = ram + '%';
      document.getElementById('disk-val').textContent = disk + '%';
      document.getElementById('ai-val').textContent = data.ai_available ? 'Online' : 'Offline';
      document.getElementById('ai-val').style.color = data.ai_available ? 'var(--success)' : 'var(--danger)';

      // Color code metrics
      setCardColor('card-cpu', cpu);
      setCardColor('card-ram', ram);
      setCardColor('card-disk', disk);
    })
    .catch(() => {});
}

function setCardColor(cardId, value) {
  const card = document.getElementById(cardId);
  if (!card) return;
  const v = parseFloat(value);
  if (v > 90) card.style.borderColor = 'var(--danger)';
  else if (v > 75) card.style.borderColor = 'var(--warning)';
  else card.style.borderColor = 'var(--success)';
}

function updateProcesses() {
  fetch('/api/processes')
    .then(r => r.json())
    .then(data => {
      const tbody = document.getElementById('process-tbody');
      if (!tbody) return;
      tbody.innerHTML = '';
      data.slice(0, 10).forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${p.pid}</td><td>${p.name ?? ''}</td><td>${(p.cpu_percent ?? 0).toFixed(1)}%</td><td>${(p.memory_percent ?? 0).toFixed(1)}%</td>`;
        tbody.appendChild(tr);
      });
    })
    .catch(() => {});
}

function addChatMessage(role, text) {
  const box = document.getElementById('chat-box');
  const div = document.createElement('div');
  div.className = 'chat-msg ' + role;
  div.textContent = (role === 'user' ? '👤 ' : '🤖 ') + text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function sendChat() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  addChatMessage('user', message);

  fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message})
  })
    .then(r => r.json())
    .then(data => {
      addChatMessage('assistant', data.response || data.error || 'No response');
    })
    .catch(e => addChatMessage('assistant', 'Error: ' + e.message));
}

// Send on Enter key
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('chat-input');
  if (input) {
    input.addEventListener('keypress', e => {
      if (e.key === 'Enter') sendChat();
    });
  }
  updateStatus();
  updateProcesses();
  setInterval(updateStatus, 3000);
  setInterval(updateProcesses, 5000);
  addChatMessage('assistant', 'Hello! I\'m Jarvis AI. How can I help you today?');
});
