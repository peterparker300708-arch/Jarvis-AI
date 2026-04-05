/* Jarvis AI - Terminal JavaScript */

const history = [];
let historyIndex = -1;

function writeLine(text, type = 'output') {
  const output = document.getElementById('terminal-output');
  const div = document.createElement('div');
  div.className = 'terminal-line ' + type;
  div.textContent = text;
  output.appendChild(div);
  output.scrollTop = output.scrollHeight;
}

function executeCommand(cmd) {
  if (!cmd.trim()) return;
  history.unshift(cmd);
  historyIndex = -1;

  writeLine('jarvis@ai:~$ ' + cmd, 'prompt');

  fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: cmd})
  })
    .then(r => r.json())
    .then(data => {
      if (data.response) {
        data.response.split('\n').forEach(line => writeLine(line, 'output'));
      }
      if (data.error) writeLine('Error: ' + data.error, 'error');
    })
    .catch(e => writeLine('Connection error: ' + e.message, 'error'));
}

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('terminal-input');
  if (!input) return;

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      executeCommand(input.value);
      input.value = '';
    } else if (e.key === 'ArrowUp') {
      if (historyIndex < history.length - 1) {
        historyIndex++;
        input.value = history[historyIndex];
      }
    } else if (e.key === 'ArrowDown') {
      if (historyIndex > 0) {
        historyIndex--;
        input.value = history[historyIndex];
      } else {
        historyIndex = -1;
        input.value = '';
      }
    }
  });

  writeLine('Jarvis AI Terminal v2.0.0', 'output');
  writeLine('Type your command or question and press Enter.', 'output');
  writeLine('', 'output');
  input.focus();
});
