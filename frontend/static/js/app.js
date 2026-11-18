/**
 * Cidadão Ativo — JavaScript da aplicação.
 *
 * Datas chegam do backend em UTC e já são exibidas no fuso de São Paulo
 * pelos templates. As páginas declaram o comportamento por atributos
 * data-* e este arquivo liga cada um deles no carregamento.
 */
(function () {
  'use strict';

  const DEFAULT_COORDS = [-14.235, -51.9253]; // centro do Brasil
  const DRAFT_KEY = 'cidadao-ativo:rascunho-chamado';
  const DEFAULT_MAP_CONFIG = {
    tileUrl: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors',
    maxZoom: 19,
  };

  // ── Utilitários ──────────────────────────────────────────────────────

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function getMapConfig() {
    const el = document.getElementById('map-config');
    try {
      return { ...DEFAULT_MAP_CONFIG, ...(el ? JSON.parse(el.textContent) : {}) };
    } catch (e) {
      return DEFAULT_MAP_CONFIG;
    }
  }

  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  /** Aviso flutuante acessível (anunciado por leitores de tela). */
  function showNotification(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container position-fixed start-50 translate-middle-x p-3 w-100';
      container.style.maxWidth = '28rem';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${type} border-0 w-100`;
    toast.setAttribute('role', type === 'danger' ? 'alert' : 'status');
    toast.setAttribute('aria-atomic', 'true');
    const wrapper = document.createElement('div');
    wrapper.className = 'd-flex';
    const body = document.createElement('div');
    body.className = 'toast-body';
    body.style.whiteSpace = 'pre-line';
    body.textContent = message;
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'btn-close btn-close-white me-2 m-auto';
    close.setAttribute('data-bs-dismiss', 'toast');
    close.setAttribute('aria-label', 'Fechar aviso');
    wrapper.append(body, close);
    toast.appendChild(wrapper);
    container.appendChild(toast);
    if (window.bootstrap && bootstrap.Toast) {
      const instance = new bootstrap.Toast(toast, { delay: 6000 });
      toast.addEventListener('hidden.bs.toast', () => toast.remove());
      instance.show();
    }
  }

  /** POST JSON com CSRF; lança Error com a mensagem do servidor. */
  async function postJson(url, payload) {
    if (!navigator.onLine) {
      throw new Error('Você está sem internet. Tente novamente quando a conexão voltar.');
    }
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
      body: JSON.stringify(payload || {}),
    });
    let data = {};
    try {
      data = await response.json();
    } catch (e) {
      // resposta sem JSON
    }
    if (!response.ok || data.success === false) {
      throw new Error(data.error || (data.errors && data.errors.join('\n')) || 'Não foi possível concluir a ação.');
    }
    return data;
  }

  function getPosition(options = {}) {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Seu aparelho não permite obter a localização. Posicione o marcador manualmente.'));
        return;
      }
      navigator.geolocation.getCurrentPosition(resolve, (error) => {
        const messages = {
          1: 'Você não permitiu o acesso à localização. Libere nas configurações do navegador.',
          2: 'Localização indisponível no momento. Verifique se o GPS está ligado.',
          3: 'A localização demorou demais. Tente de novo em um lugar com melhor sinal.',
        };
        let message = messages[error && error.code] || 'Não foi possível obter sua localização.';
        if (window.isSecureContext === false) {
          message += ' (a localização só funciona em endereços https://)';
        }
        reject(new Error(message));
      }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000, ...options });
    });
  }

  function setBusy(button, busy, busyText) {
    if (!button) return;
    if (busy) {
      button.dataset.originalHtml = button.innerHTML;
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      button.innerHTML = `<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> ${escapeHtml(busyText || 'Aguarde...')}`;
    } else {
      button.disabled = false;
      button.removeAttribute('aria-busy');
      if (button.dataset.originalHtml) button.innerHTML = button.dataset.originalHtml;
    }
  }

  // ── Mapas ────────────────────────────────────────────────────────────

  function initMap(el, center = DEFAULT_COORDS, zoom = 13) {
    const map = L.map(el, { tap: true }).setView(center, zoom);
    const tiles = getMapConfig();
    L.tileLayer(tiles.tileUrl, { maxZoom: tiles.maxZoom, attribution: tiles.attribution }).addTo(map);
    return map;
  }

  /** Mapa somente leitura com um marcador (detalhe do chamado). */
  function initStaticMap(el) {
    const lat = parseFloat(el.dataset.lat);
    const lng = parseFloat(el.dataset.lng);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return;
    const map = initMap(el, [lat, lng], 16);
    L.marker([lat, lng], { keyboard: false, interactive: false, alt: el.dataset.title || 'Local do chamado' }).addTo(map);
  }

  /** Mapa do painel do órgão: chamados e regiões com mais ocorrências. */
  function initAgencyMap(el, config) {
    const reports = Array.isArray(config.reports) ? config.reports : [];
    const heatPoints = Array.isArray(config.heatPoints) ? config.heatPoints : [];
    if (!reports.length && !heatPoints.length) return;

    const map = initMap(el, config.center ? [config.center.lat, config.center.lng] : DEFAULT_COORDS, config.center ? 12 : 4);
    if (config.bounds) {
      const bounds = L.latLngBounds(
        [config.bounds.southWest.lat, config.bounds.southWest.lng],
        [config.bounds.northEast.lat, config.bounds.northEast.lng]
      );
      map.fitBounds(bounds, { padding: [24, 24] });
    }

    heatPoints.forEach((point) => {
      L.circle([point.lat, point.lng], {
        radius: Math.min(3000, 800 + point.count * 120),
        color: '#b91c1c',
        fillColor: '#ef4444',
        weight: 1,
        fillOpacity: 0.2,
      }).addTo(map).bindTooltip(`${point.count} chamado(s) nesta região`);
    });

    reports.forEach((report) => {
      L.marker([report.lat, report.lng], { title: report.title }).addTo(map).bindPopup(
        `<strong>#${escapeHtml(report.id)} · ${escapeHtml(report.title)}</strong><br>` +
        `<small>${escapeHtml(report.category)} · ${escapeHtml(report.status)}</small><br>` +
        `<small>Aberto em ${escapeHtml(report.created_at)}</small><br>` +
        `<a href="${escapeHtml(report.detail_url)}" class="d-inline-block mt-2">Ver detalhes</a>`
      );
    });
  }

  // ── Novo chamado ─────────────────────────────────────────────────────

  function initReportForm(form) {
    const mapEl = document.getElementById('report-map-picker');
    const statusEl = document.getElementById('location-status');
    const alertBox = document.getElementById('form-alert');
    const submitBtn = form.querySelector('[type="submit"]');
    const locateBtn = document.getElementById('detect-location-btn');
    const draftNotice = document.getElementById('draft-notice');
    const map = initMap(mapEl, DEFAULT_COORDS, 4);
    let marker = null;

    function setStatus(message, tone = 'muted') {
      statusEl.textContent = message;
      statusEl.className = `small mb-2 text-${tone}`;
    }

    function showAlert(message, type) {
      alertBox.className = `alert alert-${type} mt-3`;
      alertBox.textContent = message;
      alertBox.hidden = false;
      alertBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function placeMarker(lat, lng, zoom) {
      if (marker) {
        marker.setLatLng([lat, lng]);
      } else {
        marker = L.marker([lat, lng], { draggable: true, title: 'Local do problema' }).addTo(map);
        marker.on('dragend', saveDraft);
      }
      if (zoom) map.setView([lat, lng], zoom);
      saveDraft();
    }

    async function locate(showErrors) {
      setStatus('Procurando sua localização...', 'primary');
      setBusy(locateBtn, true, 'Localizando...');
      try {
        const pos = await getPosition();
        placeMarker(pos.coords.latitude, pos.coords.longitude, 17);
        setStatus('Localização encontrada. Se precisar, toque no mapa ou arraste o marcador para ajustar.', 'success');
      } catch (err) {
        setStatus(`${err.message} Toque no mapa para marcar o local.`, 'danger');
        if (showErrors) showNotification(err.message, 'warning');
      } finally {
        setBusy(locateBtn, false);
      }
    }

    // Rascunho guardado no aparelho (sobrevive à falta de internet e ao app fechado)
    function saveDraft() {
      const data = {
        title: form.elements.title.value,
        category: form.elements.category.value,
        description: form.elements.description.value,
      };
      if (marker) {
        const { lat, lng } = marker.getLatLng();
        Object.assign(data, { lat, lng });
      }
      try {
        localStorage.setItem(DRAFT_KEY, JSON.stringify(data));
      } catch (e) {
        // armazenamento indisponível (modo privado)
      }
    }

    function restoreDraft() {
      let data = null;
      try {
        data = JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null');
      } catch (e) {
        data = null;
      }
      if (!data || !(data.title || data.description)) return false;
      ['title', 'category', 'description'].forEach((name) => {
        if (data[name]) form.elements[name].value = data[name];
      });
      if (typeof data.lat === 'number' && typeof data.lng === 'number') {
        placeMarker(data.lat, data.lng, 17);
        setStatus('Local recuperado do rascunho. Toque no mapa para mudar.', 'success');
      }
      if (draftNotice) draftNotice.hidden = false;
      return true;
    }

    function clearDraft() {
      try {
        localStorage.removeItem(DRAFT_KEY);
      } catch (e) {
        // ignorado
      }
      if (draftNotice) draftNotice.hidden = true;
    }

    map.on('click', (event) => {
      placeMarker(event.latlng.lat, event.latlng.lng);
      setStatus('Local marcado. Arraste o marcador ou toque em outro ponto para ajustar.', 'success');
    });
    form.addEventListener('input', saveDraft);
    if (locateBtn) locateBtn.addEventListener('click', () => locate(true));
    const discardBtn = document.getElementById('discard-draft-btn');
    if (discardBtn) {
      discardBtn.addEventListener('click', () => {
        form.reset();
        clearDraft();
      });
    }

    if (!restoreDraft() || !marker) {
      locate(false);
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      alertBox.hidden = true;
      if (!form.reportValidity()) return;
      if (!marker) {
        showAlert('Marque no mapa onde está o problema: toque no mapa ou use "Usar minha localização".', 'warning');
        mapEl.focus();
        return;
      }
      if (!navigator.onLine) {
        saveDraft();
        showAlert('Você está sem internet. Seu chamado ficou guardado neste aparelho: toque em "Enviar chamado" quando a conexão voltar. (A foto precisa estar selecionada no envio.)', 'warning');
        return;
      }

      const { lat, lng } = marker.getLatLng();
      setBusy(submitBtn, true, 'Enviando...');
      try {
        const geocode = await postJson('/api/geocode', { lat, lng });
        const place = geocode.data;
        if (!place || !place.valid || !place.municipio_ibge_id) {
          throw new Error('Não foi possível identificar o município deste local. Ajuste o marcador no mapa.');
        }
        const agencies = await fetch('/api/municipios/com-orgaos').then((r) => r.json());
        if (!(agencies.data || []).some((m) => m.id === place.municipio_ibge_id)) {
          throw new Error(`Local identificado em ${place.municipio_completo}, mas este município ainda não tem órgão cadastrado na plataforma.`);
        }

        const formData = new FormData(form);
        formData.set('lat', lat);
        formData.set('lng', lng);
        formData.set('municipio_ibge_id', place.municipio_ibge_id);
        formData.set('municipio_nome', place.municipio);
        formData.set('municipio_uf', place.uf);
        const response = await fetch('/api/reports/create', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCsrfToken() },
          body: formData,
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error((data.errors && data.errors.join('\n')) || data.error || 'Erro ao enviar o chamado.');
        }

        clearDraft();
        form.reset();
        map.removeLayer(marker);
        marker = null;
        showAlert(`Chamado #${data.data.id} registrado em ${place.municipio_completo}. Você pode acompanhar pelo seu painel.`, 'success');
      } catch (err) {
        const message = err instanceof TypeError ? 'Falha de conexão. Seu chamado continua guardado: tente enviar de novo.' : err.message;
        showAlert(message, 'danger');
      } finally {
        setBusy(submitBtn, false);
      }
    });
  }

  // ── Voto de urgência ─────────────────────────────────────────────────

  async function voteUrgency(button) {
    const reportId = button.dataset.voteReport;
    setBusy(button, true, 'Verificando local...');
    try {
      const pos = await getPosition({ maximumAge: 0 });
      const result = await postJson(`/api/reports/${reportId}/vote`, {
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
      });
      document.querySelectorAll(`[data-vote-count="${reportId}"]`).forEach((el) => {
        el.textContent = result.urgency_votes_count;
      });
      button.dataset.originalHtml = '<i class="bi bi-check-circle" aria-hidden="true"></i> Urgência votada';
      setBusy(button, false);
      button.disabled = true;
      button.classList.replace('btn-outline-danger', 'btn-secondary');
      showNotification('Voto de urgência registrado. Obrigado!', 'success');
    } catch (err) {
      setBusy(button, false);
      showNotification(err.message, 'danger');
    }
  }

  // ── Gestão do chamado (órgão) ────────────────────────────────────────

  function initReportManage(form) {
    const currentStatus = form.dataset.currentStatus;
    const reportId = form.dataset.reportId;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const status = form.elements.status.value;
      const comment = form.elements.comment.value.trim();
      if (status === currentStatus && !comment) {
        showNotification('Altere o status ou escreva um comentário antes de salvar.', 'warning');
        return;
      }
      const button = form.querySelector('[type="submit"]');
      setBusy(button, true, 'Salvando...');
      try {
        if (status !== currentStatus) {
          await postJson(`/api/reports/${reportId}/update`, { status, comment });
        } else {
          await postJson(`/api/reports/${reportId}/comment`, { comment });
        }
        window.location.reload();
      } catch (err) {
        setBusy(button, false);
        showNotification(err.message, 'danger');
      }
    });
  }

  // ── Conexão e app instalável ─────────────────────────────────────────

  function updateConnectionBanner() {
    const banner = document.getElementById('offline-banner');
    if (banner) banner.hidden = navigator.onLine;
  }

  function registerServiceWorker() {
    if (!('serviceWorker' in navigator) || !window.isSecureContext) return;
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {
        // sem app instalável neste navegador: o site continua funcionando normalmente
      });
    });
  }

  // ── Inicialização ────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', () => {
    updateConnectionBanner();
    window.addEventListener('online', () => {
      updateConnectionBanner();
      showNotification('Conexão restabelecida.', 'success');
    });
    window.addEventListener('offline', updateConnectionBanner);

    // Confirmação antes de enviar formulários de ações sensíveis
    document.querySelectorAll('form[data-confirm]').forEach((form) => {
      form.addEventListener('submit', (event) => {
        if (!window.confirm(form.dataset.confirm)) event.preventDefault();
      });
    });

    document.addEventListener('click', (event) => {
      const voteButton = event.target.closest('[data-vote-report]');
      if (voteButton) voteUrgency(voteButton);
      const toggle = event.target.closest('[data-toggle-password]');
      if (toggle) {
        const input = document.getElementById(toggle.dataset.togglePassword);
        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        toggle.setAttribute('aria-pressed', String(show));
        toggle.setAttribute('aria-label', show ? 'Ocultar senha' : 'Mostrar senha');
        toggle.querySelector('i').className = show ? 'bi bi-eye-slash' : 'bi bi-eye';
      }
      if (event.target.closest('a[href="/logout"]')) {
        try {
          localStorage.removeItem(DRAFT_KEY);
        } catch (e) {
          // ignorado
        }
      }
    });

    const reportForm = document.getElementById('report-form');
    if (reportForm && window.L) initReportForm(reportForm);

    const manageForm = document.getElementById('report-manage-form');
    if (manageForm) initReportManage(manageForm);

    if (window.L) {
      document.querySelectorAll('[data-static-map]').forEach(initStaticMap);
      const agencyMap = document.getElementById('agency-map');
      const agencyConfig = document.getElementById('agency-map-config');
      if (agencyMap && agencyConfig) initAgencyMap(agencyMap, JSON.parse(agencyConfig.textContent));
    }
  });

  registerServiceWorker();

  // Expostos para scripts das páginas
  window.CidadaoAtivo = { showNotification, postJson, getPosition, setBusy, escapeHtml };
})();
