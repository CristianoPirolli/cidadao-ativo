/**
 * Cidadão Ativo - Frontend JavaScript
 *
 * Nota sobre Timezone:
 * - O backend armazena todas as datas em UTC no banco de dados
 * - As datas são convertidas para America/Sao_Paulo (UTC-3) nos templates
 * - Ao usar new Date() com strings ISO do backend, especificar timezone 'America/Sao_Paulo'
 * - Formato: new Date(dateString).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })
 */

let currentMarker = null;
let currentMap = null;
let locationStatusEl = null;
const DEFAULT_COORDS = [-23.55, -46.63];

// Token CSRF exposto pelo template base (<meta name="csrf-token">)
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

// Função para mostrar notificação (melhor que alert em mobile)
function showNotification(message, type = 'info') {
  // Se Bootstrap Toast estiver disponível, usar
  if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
    // Criar container de toasts se não existir
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toast-container';
      toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
      toastContainer.style.zIndex = '9999';
      document.body.appendChild(toastContainer);
    }

    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-bg-${type} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
      </div>
    `;

    toastContainer.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 5000 });
    toast.show();

    // Remover elemento após esconder
    toastEl.addEventListener('hidden.bs.toast', () => {
      toastEl.remove();
    });
  } else {
    // Fallback para alert se Bootstrap não estiver disponível
    alert(message);
  }
}

function initMap(divId, center=DEFAULT_COORDS, zoom=null) {
  // Ajustar zoom baseado no tamanho da tela se não especificado
  const isMobile = window.innerWidth < 768;
  const defaultZoom = zoom !== null ? zoom : (isMobile ? 11 : 13);

  const map = L.map(divId).setView(center, defaultZoom);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
  return map;
}

function initCitizenPage() {
  currentMap = initMap('map');
  locationStatusEl = document.getElementById('location-status');

  const detectBtn = document.getElementById('detect-location-btn');
  if (detectBtn) {
    detectBtn.addEventListener('click', () => locateUserPosition(true));
  }

  locateUserPosition(false);

  const form = document.getElementById('report-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const alertBox = document.getElementById('form-alert');

    // Validar se há um marcador no mapa
    if (!currentMarker) {
      alertBox.className = 'alert alert-warning mt-3';
      alertBox.textContent = 'Por favor, selecione uma localização no mapa antes de enviar.';
      alertBox.classList.remove('d-none');
      return;
    }

    const {lat, lng} = currentMarker.getLatLng();

    // Detectar município a partir das coordenadas
    alertBox.className = 'alert alert-info mt-3';
    alertBox.textContent = 'Detectando município...';
    alertBox.classList.remove('d-none');

    try {
      // Fazer geocoding para obter município
      const geocodeResp = await fetch('/api/geocode', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
        body: JSON.stringify({lat, lng})
      });
      const geocodeResult = await geocodeResp.json();

      if (!geocodeResult.success || !geocodeResult.data) {
        throw new Error(geocodeResult.error || 'Não foi possível determinar o município. Tente ajustar a localização no mapa.');
      }

      const geocodeData = geocodeResult.data;

      if (!geocodeData.valid || !geocodeData.municipio_ibge_id) {
        throw new Error(geocodeData.error || 'Não foi possível determinar o município. Tente ajustar a localização no mapa.');
      }

      // Verificar se o município tem órgão cadastrado
      const orgaosResp = await fetch('/api/municipios/com-orgaos');
      const orgaosResult = await orgaosResp.json();
      const municipiosComOrgaos = orgaosResult.data || [];
      const temOrgao = municipiosComOrgaos.some(m => m.id === geocodeData.municipio_ibge_id);

      if (!temOrgao) {
        throw new Error(`Município detectado: ${geocodeData.municipio_completo}.\n\nAinda não há órgão cadastrado neste município. Por favor, selecione outro local.`);
      }

      // Adicionar dados de município ao formulário
      const fd = new FormData(form);
      fd.set('lat', lat);
      fd.set('lng', lng);
      fd.set('municipio_ibge_id', geocodeData.municipio_ibge_id);
      fd.set('municipio_nome', geocodeData.municipio);
      fd.set('municipio_uf', geocodeData.uf);

      // Enviar formulário
      alertBox.textContent = 'Enviando chamado...';

      const resp = await fetch('/api/reports/create', {
        method: 'POST',
        headers: {'X-CSRFToken': getCsrfToken()},
        body: fd
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error((data && data.errors) ? data.errors.join('\n') : 'Erro ao enviar');

      alertBox.className = 'alert alert-success mt-3';
      alertBox.textContent = `Chamado registrado com sucesso em ${geocodeData.municipio_completo}!`;
      alertBox.classList.remove('d-none');
      form.reset();

      // Remover marcador após sucesso
      if (currentMarker) {
        currentMap.removeLayer(currentMarker);
        currentMarker = null;
      }
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

function setLocationStatus(message, tone='muted') {
  if (!locationStatusEl) return;
  locationStatusEl.textContent = message || '';
  const baseClass = 'd-block mt-2 small';
  locationStatusEl.className = `${baseClass} text-${tone}`;
}

function locateUserPosition(triggeredByButton=false) {
  if (!navigator.geolocation) {
    setMarker(...DEFAULT_COORDS);
    setLocationStatus('Seu navegador não suporta geolocalização. Posicione o marcador manualmente.', 'danger');
    if (triggeredByButton) {
      showNotification('Geolocalização não suportada neste dispositivo. Posicione o marcador manualmente.', 'warning');
    }
    return;
  }

  setLocationStatus('Detectando sua localização...', 'primary');

  if (window.isSecureContext === false && triggeredByButton) {
    showNotification('Para detectar automaticamente sua localização é necessário acessar a plataforma via HTTPS.', 'warning');
  }

  navigator.geolocation.getCurrentPosition((pos) => {
    const lat = pos.coords.latitude;
    const lng = pos.coords.longitude;
    setMarker(lat, lng);
    currentMap.setView([lat, lng], 17);
    setLocationStatus('Localização detectada com sucesso.', 'success');
  }, (error) => {
    let message = 'Não foi possível obter sua localização. Verifique as permissões do navegador.';
    if (error && typeof error.code === 'number') {
      if (error.code === error.PERMISSION_DENIED) {
        message = 'Você negou o acesso à localização. Libere o acesso nas configurações do navegador e tente novamente.';
      } else if (error.code === error.POSITION_UNAVAILABLE) {
        message = 'O serviço de localização está indisponível no momento. Tente novamente em instantes.';
      } else if (error.code === error.TIMEOUT) {
        message = 'Tempo de localização excedido. Certifique-se de estar em área com sinal e tente novamente.';
      }
    }
    setLocationStatus(message, 'danger');
    if (!currentMarker) {
      setMarker(...DEFAULT_COORDS);
    }
    if (triggeredByButton) {
      showNotification(message, 'danger');
    }
  }, {
    enableHighAccuracy: true,
    timeout: 10000
  });
}

function initAgencyDashboardMap(config) {
  const heatPoints = Array.isArray(config?.heatPoints) ? config.heatPoints : [];
  const reportPoints = Array.isArray(config?.reports) ? config.reports : [];

  if (!config || (!heatPoints.length && !reportPoints.length)) {
    return;
  }

  const container = document.getElementById('agency-map');
  if (!container) {
    return;
  }

  const defaultCenter = [-14.235004, -51.925282];
  let center = null;

  if (config.center) {
    center = [config.center.lat, config.center.lng];
  } else if (heatPoints.length) {
    center = [heatPoints[0].lat, heatPoints[0].lng];
  }

  const zoom = center ? 12 : 5;
  const map = initMap('agency-map', center || defaultCenter, zoom);

  const isMobile = window.innerWidth < 768;
  const padding = isMobile ? [40, 40] : [20, 20];

  if (config.bounds && config.bounds.southWest && config.bounds.northEast) {
    const bounds = L.latLngBounds(
      [config.bounds.southWest.lat, config.bounds.southWest.lng],
      [config.bounds.northEast.lat, config.bounds.northEast.lng]
    );
    map.fitBounds(bounds, { padding });
    map.setMaxBounds(bounds.pad(0.25));
  } else if (heatPoints.length) {
    const heatBounds = L.latLngBounds(heatPoints.map(point => [point.lat, point.lng]));
    map.fitBounds(heatBounds, { padding });
    map.setMaxBounds(heatBounds.pad(0.25));
  }

  if (heatPoints.length) {
    heatPoints.forEach((point) => {
      const radius = Math.min(3000, 800 + point.count * 120);
      const circle = L.circle([point.lat, point.lng], {
        radius,
        color: 'rgba(220, 53, 69, 0.8)',
        fillColor: 'rgba(220, 53, 69, 0.25)',
        weight: 1,
        fillOpacity: 0.25,
      }).addTo(map);
      circle.bindTooltip(`${point.count} chamados próximos (${point.label})`, { direction: 'top' });
    });
  }

  reportPoints.forEach((report) => {
    const marker = L.marker([report.lat, report.lng]).addTo(map);
    const popup = `
      <strong>#${report.id} - ${report.title}</strong><br>
      <small>${report.category} · ${report.status}</small><br>
      <small>Aberto em: ${report.created_at}</small><br>
      <a href="${report.detail_url}" class="mt-2 d-inline-block">Ver detalhes</a>
    `;
    marker.bindPopup(popup);
  });
}


document.addEventListener('DOMContentLoaded', () => {
  if (window.agencyMapConfig) {
    initAgencyDashboardMap(window.agencyMapConfig);
  }
});
