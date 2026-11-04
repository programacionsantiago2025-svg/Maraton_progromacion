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
      const detail = data && data.detail;
      if (typeof detail === 'string') throw new Error(detail);
      // Errores de validación de Pydantic: se muestra el primer mensaje legible
      if (Array.isArray(detail) && detail.length) {
        throw new Error(String(detail[0].msg || '').replace(/^Value error, /, '') || 'Datos inválidos');
      }
      throw new Error('Ocurrió un error inesperado');
    }
    return data;
  }

  function showToast(message) {
    let toast = document.getElementById('toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'toast';
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      toast.className = 'fixed z-[1400] top-20 inset-x-4 mx-auto max-w-md bg-slate-100 text-slate-900 text-sm font-medium rounded-lg px-4 py-3 shadow-lg';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.remove('hidden');
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.add('hidden'), 4000);
  }

  // ---------- Estado de sesión en la barra superior ----------
  const authLink = document.getElementById('auth-link');
  const openContactsBtn = document.getElementById('open-contacts');
  if (openContactsBtn && getToken()) openContactsBtn.classList.remove('hidden');
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

  // ---------- Contactos de emergencia en el registro ----------
  const registerContacts = document.getElementById('register-contacts');
  const addContactRowBtn = document.getElementById('add-contact-row');
  const MAX_REGISTER_CONTACTS = 3;

  function addContactRow() {
    const index = registerContacts.children.length + 1;
    const row = document.createElement('div');
    row.className = 'rounded-lg bg-slate-800/60 p-3 space-y-2';
    row.dataset.contactRow = '';

    const title = document.createElement('p');
    title.className = 'text-sm font-semibold text-slate-200';
    title.textContent = index === 1 ? 'Contacto 1 (obligatorio)' : `Contacto ${index} (opcional)`;

    const nameLabel = document.createElement('label');
    nameLabel.className = 'block text-sm mb-1';
    nameLabel.htmlFor = `rc-name-${index}`;
    nameLabel.textContent = 'Nombre (ej. Mamá)';
    const nameInput = document.createElement('input');
    nameInput.id = `rc-name-${index}`;
    nameInput.type = 'text';
    nameInput.maxLength = 120;
    nameInput.required = index === 1;
    nameInput.autocomplete = 'off';
    nameInput.dataset.field = 'name';
    nameInput.className = 'w-full min-h-[44px] rounded-lg bg-slate-800 border border-slate-600 px-3 text-base focus-visible:outline';

    const phoneLabel = document.createElement('label');
    phoneLabel.className = 'block text-sm mb-1';
    phoneLabel.htmlFor = `rc-phone-${index}`;
    phoneLabel.textContent = 'Celular con WhatsApp';
    const phoneWrap = document.createElement('div');
    phoneWrap.className = 'flex';
    const prefix = document.createElement('span');
    prefix.className = 'flex items-center px-3 rounded-l-lg bg-slate-700 border border-slate-600 text-slate-200';
    prefix.setAttribute('aria-hidden', 'true');
    prefix.textContent = '+57';
    const phoneInput = document.createElement('input');
    phoneInput.id = `rc-phone-${index}`;
    phoneInput.type = 'tel';
    phoneInput.inputMode = 'tel';
    phoneInput.maxLength = 20;
    phoneInput.required = index === 1;
    phoneInput.placeholder = '300 123 4567';
    phoneInput.autocomplete = 'off';
    phoneInput.dataset.field = 'phone';
    phoneInput.className = 'w-full min-h-[44px] rounded-r-lg bg-slate-800 border border-l-0 border-slate-600 px-3 text-base placeholder-slate-400 focus-visible:outline';
    phoneWrap.append(prefix, phoneInput);

    row.append(title, nameLabel, nameInput, phoneLabel, phoneWrap);
    registerContacts.appendChild(row);
    addContactRowBtn.classList.toggle('hidden', registerContacts.children.length >= MAX_REGISTER_CONTACTS);
  }

  function collectRegisterContacts() {
    const contacts = [];
    registerContacts.querySelectorAll('[data-contact-row]').forEach((row) => {
      const name = row.querySelector('[data-field="name"]').value.trim();
      const phone = row.querySelector('[data-field="phone"]').value.trim();
      if (!name && !phone) return;
      if (!name || !phone) throw new Error('Completa nombre y celular de cada contacto, o deja la fila vacía.');
      contacts.push({ name, phone });
    });
    return contacts;
  }

  if (registerContacts && addContactRowBtn) {
    addContactRow();
    addContactRowBtn.addEventListener('click', addContactRow);
  }

  if (registerForm) {
    registerForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      authStatus.textContent = 'Creando cuenta…';
      const name = document.getElementById('register-name').value;
      const email = document.getElementById('register-email').value;
      const password = document.getElementById('register-password').value;
      try {
        const contacts = collectRegisterContacts();
        await apiFetch('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify({ name, email, password, contacts }),
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
    card.addEventListener('click', () => {
      if (window.RutaMap) window.RutaMap.highlightRoute(currentPolylines, index);
    });
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
        // Si el mapa no cargó, igual se muestran las tarjetas con las rutas
        currentPolylines = window.RutaMap ? window.RutaMap.drawRoutes(data.rutas) : [];
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
        showToast(err.message);
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
          showToast(err.message);
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
        showToast(err.message);
      }
    });
  }

  // ---------- SOS ----------
  const sosBtn = document.getElementById('sos-btn');
  const sosHint = document.getElementById('sos-hint');
  let sosTimer = null;

  const sosStatus = document.getElementById('sos-status');
  const sosActions = document.getElementById('sos-actions');

  function sosLink(href, text, className) {
    const a = document.createElement('a');
    a.href = href;
    a.target = '_blank';
    a.rel = 'noopener';
    a.className = `flex items-center justify-center w-full min-h-[56px] rounded-xl text-lg font-bold text-center px-3 focus-visible:outline ${className}`;
    a.textContent = text;
    return a;
  }

  function locateWithTimeout(ms) {
    return Promise.race([
      window.RutaMap.locateUser(),
      new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), ms)),
    ]);
  }

  async function triggerSOS() {
    if (!getToken()) {
      window.location.href = '/login';
      return;
    }
    if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
    sosActions.textContent = '';
    sosStatus.textContent = 'Obteniendo tu ubicación…';
    openModal('sos-modal');

    let location = null;
    try {
      location = await locateWithTimeout(5000);
    } catch (err) {
      location = null;
    }

    try {
      const data = await apiFetch('/api/sos', { method: 'POST', body: JSON.stringify(location || {}) });
      const sinUbicacion = location ? '' : ' No pudimos obtener tu ubicación; el mensaje irá sin ella.';
      if (data.contactos.length) {
        sosStatus.textContent = `Toca cada contacto para enviarle el mensaje por WhatsApp.${sinUbicacion}`;
        data.contactos.forEach((c) => {
          sosActions.appendChild(sosLink(c.whatsapp_url, `Avisar a ${c.name} por WhatsApp`, 'bg-green-700 hover:bg-green-600 text-white'));
        });
      } else {
        sosStatus.textContent = `Aún no tienes contactos de emergencia.${sinUbicacion}`;
        const addBtn = document.createElement('button');
        addBtn.type = 'button';
        addBtn.className = 'w-full min-h-[56px] rounded-xl bg-green-700 hover:bg-green-600 text-white text-lg font-bold focus-visible:outline';
        addBtn.textContent = 'Agregar contactos';
        addBtn.addEventListener('click', () => {
          closeModal('sos-modal');
          openContactsModal();
        });
        sosActions.appendChild(addBtn);
      }
      sosActions.appendChild(sosLink(data.whatsapp_compartir, 'Enviar a otra persona por WhatsApp', 'bg-slate-700 hover:bg-slate-600 text-white text-base'));
    } catch (err) {
      sosStatus.textContent = `${err.message}. Si estás en peligro, llama al 123.`;
    }
  }

  // ---------- Contactos de emergencia (modal) ----------
  const contactsList = document.getElementById('contacts-list');
  const contactForm = document.getElementById('contact-form');
  const contactsStatus = document.getElementById('contacts-status');

  async function loadContacts() {
    contactsList.textContent = '';
    const contactos = await apiFetch('/api/contacts');
    if (!contactos.length) {
      const empty = document.createElement('li');
      empty.className = 'text-sm text-slate-400';
      empty.textContent = 'Todavía no has agregado contactos.';
      contactsList.appendChild(empty);
    }
    contactos.forEach((c) => {
      const li = document.createElement('li');
      li.className = 'flex items-center justify-between gap-2 rounded-lg bg-slate-800 px-3 py-2';
      const info = document.createElement('div');
      const name = document.createElement('p');
      name.className = 'font-semibold';
      name.textContent = c.name;
      const phone = document.createElement('p');
      phone.className = 'text-sm text-slate-300';
      phone.textContent = `+${c.phone}`;
      info.append(name, phone);
      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'min-h-[44px] px-3 rounded-lg bg-slate-700 hover:bg-red-700 text-sm font-medium focus-visible:outline';
      del.textContent = 'Eliminar';
      del.setAttribute('aria-label', `Eliminar a ${c.name}`);
      del.addEventListener('click', async () => {
        try {
          await apiFetch(`/api/contacts/${c.id}`, { method: 'DELETE' });
          await loadContacts();
        } catch (err) {
          contactsStatus.textContent = err.message;
        }
      });
      li.append(info, del);
      contactsList.appendChild(li);
    });
  }

  async function openContactsModal() {
    contactsStatus.textContent = '';
    openModal('contacts-modal');
    try {
      await loadContacts();
    } catch (err) {
      contactsStatus.textContent = err.message;
    }
  }

  if (openContactsBtn) openContactsBtn.addEventListener('click', openContactsModal);

  if (contactForm) {
    contactForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const name = document.getElementById('contact-name').value.trim();
      const phone = document.getElementById('contact-phone').value.trim();
      try {
        await apiFetch('/api/contacts', { method: 'POST', body: JSON.stringify({ name, phone }) });
        contactForm.reset();
        contactsStatus.textContent = 'Contacto agregado.';
        await loadContacts();
      } catch (err) {
        contactsStatus.textContent = err.message;
      }
    });
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
    // En móvil, el menú contextual del toque largo cancelaría la pulsación de 1 s
    sosBtn.addEventListener('contextmenu', (ev) => ev.preventDefault());
  }
})();
