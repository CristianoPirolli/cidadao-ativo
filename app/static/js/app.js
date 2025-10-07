let currentMarker = null;
let currentMap = null;

function initMap(divId, center=[-23.55, -46.63], zoom=13) {
  const map = L.map(divId).setView(center, zoom);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
  return map;
}

function initCitizenPage() {
  currentMap = initMap('map');
  // Try geolocation
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition((pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      setMarker(lat, lng);
      currentMap.setView([lat, lng], 17);
    }, () => {
      // Default marker in center
      setMarker(-23.55, -46.63);
    });
  } else {
    setMarker(-23.55, -46.63);
  }

  const form = document.getElementById('report-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    if (currentMarker) {
      const {lat, lng} = currentMarker.getLatLng();
      fd.set('lat', lat);
      fd.set('lng', lng);
    }
    const alertBox = document.getElementById('form-alert');
    try {
      const resp = await fetch('/api/reports', { method: 'POST', body: fd });
      const data = await resp.json();
      if (!resp.ok) throw new Error((data && data.errors) ? data.errors.join('\n') : 'Erro ao enviar');
      alertBox.className = 'alert alert-success mt-3';
      alertBox.textContent = 'Chamado registrado com sucesso!';
      alertBox.classList.remove('d-none');
      form.reset();
    } catch (err) {
      alertBox.className = 'alert alert-danger mt-3';
      alertBox.textContent = err.message;
      alertBox.classList.remove('d-none');
    }
  });
}

function setMarker(lat, lng) {
  if (!currentMap) return;
  if (currentMarker) currentMap.removeLayer(currentMarker);
  currentMarker = L.marker([lat, lng], { draggable: true }).addTo(currentMap);
}

function badgeForStatus(status) {
  const cls = {
    'aberto': 'bg-danger',
    'em_execucao': 'bg-warning text-dark',
    'resolvido': 'bg-success'
  }[status] || 'bg-secondary';
  return `<span class="badge ${cls}">${status.replace('_',' ')}</span>`;
}

async function fetchReports() {
  const resp = await fetch('/api/reports');
  return await resp.json();
}

async function updateStatus(id, status) {
  const resp = await fetch(`/api/reports/${id}`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({status})
  });
  return await resp.json();
}

async function initAdminPage() {
  const map = initMap('admin-map', [-23.55,-46.63], 12);
  const reports = await fetchReports();

  reports.forEach(r => {
    const marker = L.marker([r.lat, r.lng]).addTo(map);
    const img = r.image_url ? `<img src="${r.image_url}" alt="" style="max-width:200px;display:block;margin-bottom:6px;">` : '';
    marker.bindPopup(`
      <strong>${r.title}</strong><br>
      <small>${r.category}</small><br>
      ${img}
      <em>${r.description}</em><br>
      Status: ${badgeForStatus(r.status)}
    `);
  });

  const list = document.getElementById('reports-list');
  list.innerHTML = reports.map(r => `
    <div class="border rounded p-3 mb-2">
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <strong>#${r.id} — ${r.title}</strong><br>
          <small>${r.category} • ${new Date(r.created_at).toLocaleString()}</small>
          <div>Status: ${badgeForStatus(r.status)}</div>
        </div>
        <div class="btn-group">
          <button class="btn btn-sm btn-outline-danger" onclick="onSetStatus(${r.id}, 'aberto')">Aberto</button>
          <button class="btn btn-sm btn-outline-warning" onclick="onSetStatus(${r.id}, 'em_execucao')">Em execução</button>
          <button class="btn btn-sm btn-outline-success" onclick="onSetStatus(${r.id}, 'resolvido')">Resolvido</button>
        </div>
      </div>
    </div>
  `).join('');
}

async function onSetStatus(id, status) {
  const updated = await updateStatus(id, status);
  // naive refresh
  location.reload();
}