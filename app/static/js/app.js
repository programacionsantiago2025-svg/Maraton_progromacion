// app.js - autenticación, reportes, Modo Guardián, SOS y búsqueda de rutas
(function () {
  const TOKEN_KEY = 'rutasegura_token';

  function getToken() {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch (err) {
      return null;
    }
  }

  function setToken(token) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch (err) {
      console.warn('No se pudo guardar la sesión (almacenamiento no disponible)');
    }
  }

  function clearToken() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch (err) {
      /* no-op */
    }
  }

  async function apiFetch(path, options = {}) {
    const headers = Object.assign({}, options.headers || {});
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (options.body && !(options.body instanceof URLSearchParams)) {
      headers['Content-Type'] = 'application/json';
    }
    const resp = await fetch(path, Object.assign({}, options, { headers }));
    let data = null;
    try {
      data = await resp.json();
    } catch (err) {
      data = null;
    }
    if (!resp.ok) {
      const message = (data && data.detail) || 'Ocurrió un error inesperado';
      throw new Error(typeof message === 'string' ? message : 'Ocurrió un error inesperado');
    }
    return data;
  }

  // ---------- Estado de sesión en la barra superior ----------
  const authLink = document.getElementById('auth-link');
  if (authLink && getToken()) {
    authLink.textContent = 'Cerrar sesión';
    authLink.setAttribute('href', '#');
    authLink.addEventListener('click', (ev) => {
      ev.preventDefault();
      clearToken();
      window.location.reload();
    });
  }

  // ---------- Página de login/registro ----------
  const tabLogin = document.getElementById('tab-login');
  const tabRegister = document.getElementById('tab-register');
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const authStatus = document.getElementById('auth-status');

  function switchTab(which) {
    const isLogin = which === 'login';
    loginForm.classList.toggle('hidden', !isLogin);
    registerForm.classList.toggle('hidden', isLogin);
    tabLogin.setAttribute('aria-selected', String(isLogin));
    tabRegister.setAttribute('aria-selected', String(!isLogin));
    tabLogin.classList.toggle('bg-slate-700', isLogin);
    tabLogin.classList.toggle('bg-slate-800', !isLogin);
    tabRegister.classList.toggle('bg-slate-700', !isLogin);
    tabRegister.classList.toggle('bg-slate-800', isLogin);
  }

  if (tabLogin && tabRegister) {
    tabLogin.addEventListener('click', () => switchTab('login'));
    tabRegister.addEventListener('click', () => switchTab('register'));
  }

  if (loginForm) {
    loginForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      authStatus.textContent = 'Entrando…';
      const email = document.getElementById('login-email').value;
      const password = document.getElementById('login-password').value;
      try {
        const body = new URLSearchParams({ username: email, password });
        const data = await apiFetch('/api/auth/login', { method: 'POST', body });
        setToken(data.access_token);
        authStatus.textContent = '¡Bienvenida de nuevo!';
        window.location.href = '/';
      } catch (err) {
        authStatus.textContent = err.message;
      }
    });
  }

  if (registerForm) {
    registerForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      authStatus.textContent = 'Creando cuenta…';
      const name = document.getElementById('register-name').value;
      const email = document.getElementById('register-email').value;
      const password = document.getElementById('register-password').value;
      try {
        await apiFetch('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify({ name, email, password }),
        });
        const body = new URLSearchParams({ username: email, password });
        const data = await apiFetch('/api/auth/login', { method: 'POST', body });
        setToken(data.access_token);
        window.location.href = '/';
      } catch (err) {
        authStatus.textContent = err.message;
      }
    });
  }

  // ---------- Panel inferior colapsable ----------
  const sheetToggle = document.getElementById('sheet-toggle');
  const sheetContent = document.getElementById('sheet-content');
  if (sheetToggle && sheetContent) {
    sheetToggle.addEventListener('click', () => {
      const collapsed = sheetContent.classList.toggle('hidden');
      sheetToggle.setAttribute('aria-expanded', String(!collapsed));
    });
  }

  // ---------- Búsqueda de rutas ----------
  const routeForm = document.getElementById('route-form');
  const routeStatus = document.getElementById('route-status');
  const routeResults = document.getElementById('route-results');
  let currentPolylines = [];

  function renderRouteCard(ruta, index) {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'w-full text-left rounded-lg p-3 border-2 focus-visible:outline bg-slate-800/80';
    card.style.borderColor = ruta.isn >= 70 ? '#22c55e' : ruta.isn >= 40 ? '#f59e0b' : '#ef4444';
    card.setAttribute('aria-label', `Ruta ${index + 1}, índice de seguridad nocturna ${ruta.isn} de 100`);

    const header = document.createElement('div');
    header.className = 'flex justify-between items-center font-semibold';
    const title = document.createElement('span');
    title.textContent = ruta.es_mas_segura ? '🟢 Ruta más segura' : `Ruta alternativa ${index + 1}`;
    const isnBadge = document.createElement('span');
    isnBadge.textContent = `ISN ${ruta.isn}`;
    header.appendChild(title);
    header.appendChild(isnBadge);

    const meta = document.createElement('div');
    meta.className = 'text-xs text-slate-300 mt-1';
    meta.textContent = `${(ruta.distance_m / 1000).toFixed(2)} km · ${Math.round(ruta.duration_s / 60)} min`;

    const explanation = document.createElement('p');
    explanation.className = 'text-sm text-slate-200 mt-2';
    explanation.textContent = ruta.breakdown.explicacion;

    card.appendChild(header);
    card.appendChild(meta);
    card.appendChild(explanation);
    card.addEventListener('click', () => window.RutaMap.highlightRoute(currentPolylines, index));
    return card;
  }

  if (routeForm) {
    routeForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const origin = document.getElementById('origin').value;
      const destination = document.getElementById('destination').value;
      routeStatus.textContent = 'Buscando rutas seguras…';
      routeResults.innerHTML = '';
      try {
        const params = new URLSearchParams({ origin, destination });
        const data = await apiFetch(`/api/routes?${params.toString()}`);
        routeStatus.textContent = `${data.rutas.length} ruta(s) encontrada(s).`;
        currentPolylines = window.RutaMap.drawRoutes(data.rutas);
        data.rutas.forEach((ruta, index) => routeResults.appendChild(renderRouteCard(ruta, index)));
      } catch (err) {
        routeStatus.textContent = err.message;
      }
    });
  }

  // ---------- Modales genéricos ----------
  function openModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.remove('hidden');
    const focusable = modal.querySelector('input, select, textarea, button');
    if (focusable) focusable.focus();
  }

  function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('hidden');
  }

  document.querySelectorAll('[data-close-modal]').forEach((btn) => {
    btn.addEventListener('click', () => closeModal(btn.getAttribute('data-close-modal')));
  });

  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape') {
      document.querySelectorAll('[role="dialog"]').forEach((modal) => modal.classList.add('hidden'));
    }
  });

  // ---------- Reportar ----------
  const openReportBtn = document.getElementById('open-report-modal');
  const reportForm = document.getElementById('report-form');
  const severityInput = document.getElementById('report-severity');
  const severityValue = document.getElementById('severity-value');
  const reportLocationStatus = document.getElementById('report-location-status');
  let reportLocation = null;

  if (severityInput && severityValue) {
    severityInput.addEventListener('input', () => {
      severityValue.textContent = severityInput.value;
    });
  }

  if (openReportBtn) {
    openReportBtn.addEventListener('click', async () => {
      openModal('report-modal');
      reportLocationStatus.textContent = 'Obteniendo tu ubicación…';
      try {
        reportLocation = await window.RutaMap.locateUser();
        reportLocationStatus.textContent = 'Ubicación obtenida ✓';
      } catch (err) {
        reportLocation = null;
        reportLocationStatus.textContent = 'No se pudo obtener tu ubicación; se usará el centro del mapa.';
      }
    });
  }

  if (reportForm) {
    reportForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const center = window.RutaMap.map.getCenter();
      const location = reportLocation || { lat: center.lat, lng: center.lng };
      const payload = {
        type: document.getElementById('report-type').value,
        severity: Number(document.getElementById('report-severity').value),
        description: document.getElementById('report-description').value || null,
        lat: location.lat,
        lng: location.lng,
      };
      try {
        const report = await apiFetch('/api/reports', { method: 'POST', body: JSON.stringify(payload) });
        window.RutaMap.addReportMarker(report);
        closeModal('report-modal');
        reportForm.reset();
        severityValue.textContent = '3';
      } catch (err) {
        alert(err.message);
      }
    });
  }

  // ---------- Modo Guardián ----------
  const openGuardianBtn = document.getElementById('open-guardian-modal');
  const guardianForm = document.getElementById('guardian-form');
  const guardianStatus = document.getElementById('guardian-status');
  let guardianSessionId = null;
  let guardianInterval = null;

  if (openGuardianBtn) {
    openGuardianBtn.addEventListener('click', () => {
      if (!getToken()) {
        window.location.href = '/login';
        return;
      }
      openModal('guardian-modal');
    });
  }

  function renderGuardianStatus(session) {
    guardianStatus.classList.remove('hidden');
    guardianStatus.textContent = '';

    const info = document.createElement('p');
    if (session.status === 'active') {
      const remainingMs = new Date(session.eta_at).getTime() - Date.now();
      const minutes = Math.max(0, Math.ceil(remainingMs / 60000));
      info.textContent = `Guardián activo: llegada estimada en ${minutes} min.`;
    } else if (session.status === 'alert') {
      info.textContent = 'No hiciste check-in a tiempo. Si estás bien, confirma que llegaste.';
    } else {
      info.textContent = 'Llegaste a salvo. ¡Buen viaje!';
    }
    guardianStatus.appendChild(info);

    if (session.status !== 'arrived') {
      const arrivedBtn = document.createElement('button');
      arrivedBtn.type = 'button';
      arrivedBtn.textContent = 'Llegué a salvo';
      arrivedBtn.className = 'w-full min-h-[44px] rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold focus-visible:outline';
      arrivedBtn.addEventListener('click', async () => {
        try {
          await apiFetch(`/api/guardian/${session.id}/arrived`, { method: 'POST' });
          if (guardianInterval) clearInterval(guardianInterval);
          renderGuardianStatus(Object.assign({}, session, { status: 'arrived' }));
        } catch (err) {
          alert(err.message);
        }
      });
      guardianStatus.appendChild(arrivedBtn);
    }
  }

  async function pollGuardian() {
    if (!guardianSessionId) return;
    try {
      const session = await apiFetch(`/api/guardian/${guardianSessionId}`);
      renderGuardianStatus(session);
      if (session.status !== 'active' && guardianInterval) clearInterval(guardianInterval);
    } catch (err) {
      console.error('No se pudo actualizar el estado del guardián', err);
    }
  }

  if (guardianForm) {
    guardianForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const minutes = Number(document.getElementById('guardian-minutes').value);
      try {
        const location = await window.RutaMap.locateUser();
        const session = await apiFetch('/api/guardian/start', {
          method: 'POST',
          body: JSON.stringify({ minutes, lat: location.lat, lng: location.lng }),
        });
        guardianSessionId = session.id;
        closeModal('guardian-modal');
        renderGuardianStatus(session);
        if (guardianInterval) clearInterval(guardianInterval);
        guardianInterval = setInterval(pollGuardian, 30000);
      } catch (err) {
        alert(err.message);
      }
    });
  }

  // ---------- SOS ----------
  const sosBtn = document.getElementById('sos-btn');
  const sosHint = document.getElementById('sos-hint');
  let sosTimer = null;

  async function triggerSOS() {
    if (!getToken()) {
      window.location.href = '/login';
      return;
    }
    if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
    try {
      const data = await apiFetch('/api/sos', { method: 'POST' });
      const contactos = data.contactos_notificados.length ? data.contactos_notificados.join(', ') : 'ninguno registrado';
      alert(`${data.mensaje}\n\nContactos notificados: ${contactos}`);
    } catch (err) {
      alert(err.message);
    }
  }

  if (sosBtn) {
    const startHold = () => {
      sosHint.classList.remove('hidden');
      sosTimer = setTimeout(() => {
        sosHint.classList.add('hidden');
        triggerSOS();
      }, 1000);
    };
    const cancelHold = () => {
      sosHint.classList.add('hidden');
      if (sosTimer) clearTimeout(sosTimer);
    };
    sosBtn.addEventListener('pointerdown', startHold);
    sosBtn.addEventListener('pointerup', cancelHold);
    sosBtn.addEventListener('pointerleave', cancelHold);
    sosBtn.addEventListener('pointercancel', cancelHold);
  }
})();
