/* Jarvis AI - Settings JavaScript */

function saveSettings() {
  const form = document.getElementById('settings-form');
  const data = {};
  new FormData(form).forEach((v, k) => { data[k] = v; });

  const promises = Object.entries(data).map(([key, value]) =>
    fetch('/api/preferences', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({key, value: String(value)})
    })
  );

  Promise.all(promises)
    .then(() => alert('Settings saved!'))
    .catch(e => alert('Error: ' + e.message));
}

document.addEventListener('DOMContentLoaded', () => {
  fetch('/api/preferences')
    .then(r => r.json())
    .then(prefs => {
      const themeSelect = document.getElementById('theme-select');
      if (themeSelect && prefs.theme) themeSelect.value = prefs.theme;
      const desktopNotif = document.getElementById('desktop-notif');
      if (desktopNotif) desktopNotif.checked = prefs.desktop_notifications === 'true';
    })
    .catch(() => {});
});
