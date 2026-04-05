/* Jarvis AI - Analytics JavaScript */

document.addEventListener('DOMContentLoaded', () => {
  loadProfile();
  loadHistory();
});

function loadProfile() {
  fetch('/api/profile')
    .then(r => r.json())
    .then(data => {
      document.getElementById('total-commands').textContent = data.total_commands ?? '--';
      document.getElementById('success-rate').textContent =
        data.success_rate !== undefined ? (data.success_rate * 100).toFixed(0) + '%' : '--';
      document.getElementById('session-time').textContent =
        data.session_duration_minutes !== undefined ? data.session_duration_minutes + 'm' : '--';

      const tbody = document.getElementById('categories-tbody');
      if (tbody && data.top_categories) {
        tbody.innerHTML = '';
        data.top_categories.forEach(c => {
          const tr = document.createElement('tr');
          tr.innerHTML = `<td>${c.category}</td><td>${c.count}</td>`;
          tbody.appendChild(tr);
        });
      }
    })
    .catch(() => {});
}

function loadHistory() {
  fetch('/api/history?limit=20')
    .then(r => r.json())
    .then(data => {
      const tbody = document.getElementById('history-tbody');
      if (!tbody) return;
      tbody.innerHTML = '';
      (Array.isArray(data) ? data : []).forEach(item => {
        const time = item.created_at ? new Date(item.created_at).toLocaleTimeString() : '';
        const status = item.success ? '✅' : '❌';
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${time}</td><td>${item.command ?? ''}</td><td>${item.category ?? ''}</td><td>${status}</td>`;
        tbody.appendChild(tr);
      });
    })
    .catch(() => {});
}
