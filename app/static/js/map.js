// map.js - inicialización del mapa Leaflet y capas de RutaSegura
(function () {
  const DEFAULT_CENTER = [4.6097, -74.0817]; // Bogotá
  const DEFAULT_ZOOM = 13;

  if (typeof window.L === 'undefined') {
    console.error('Leaflet no se cargó: el mapa no está disponible');
    const errorBox = document.getElementById('map-error');
    if (errorBox) {
      errorBox.textContent = 'No se pudo cargar el mapa. Recarga la página.';
      errorBox.classList.remove('hidden');
    }
    return;
  }

  const map = L.map('map', {
    center: DEFAULT_CENTER,
    zoom: DEFAULT_ZOOM,
    zoomControl: true,
    attributionControl: false,
  });

  // Arriba a la derecha: abajo la taparía el panel, y la atribución es obligatoria (ODbL)
  L.control.attribution({ position: 'topright' }).addTo(map);

  // Tiles servidos por nuestro backend (proxy con caché de OpenStreetMap)
  const baseTiles = L.tileLayer('/tiles/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    className: 'map-tiles-dark',
    maxZoom: 19,
  }).addTo(map);

  const mapError = document.getElementById('map-error');
  baseTiles.on('tileerror', () => mapError.classList.remove('hidden'));
  baseTiles.on('tileload', () => mapError.classList.add('hidden'));

  const safePointsLayer = L.layerGroup().addTo(map);
  const reportsLayer = L.layerGroup().addTo(map);
  const routesLayer = L.layerGroup().addTo(map);
  const endpointsLayer = L.layerGroup().addTo(map);

  const SAFE_POINT_STYLE = {
    cai: { color: '#38bdf8', label: 'CAI' },
    farmacia: { color: '#34d399', label: 'Farmacia' },
    tienda: { color: '#fb923c', label: 'Tienda' },
    gasolinera: { color: '#a78bfa', label: 'Gasolinera' },
  };

  const REPORT_STYLE = {
    poca_luz: { color: '#fbbf24', label: 'Poca luz' },
    acoso: { color: '#ef4444', label: 'Acoso' },
    calle_sola: { color: '#f97316', label: 'Calle sola' },
    zona_segura: { color: '#22c55e', label: 'Zona segura' },
  };

  function isnColor(isn) {
    if (isn >= 70) return '#22c55e';
    if (isn >= 40) return '#f59e0b';
    return '#ef4444';
  }

  function buildPopup(titleText, extraLines) {
    const wrap = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = titleText;
    wrap.appendChild(title);
    (extraLines || []).forEach((line) => {
      wrap.appendChild(document.createElement('br'));
      const span = document.createElement('span');
      span.textContent = line;
      wrap.appendChild(span);
    });
    return wrap;
  }

  function safePointMarker(point) {
    const style = SAFE_POINT_STYLE[point.kind] || { color: '#94a3b8', label: point.kind };
    const marker = L.circleMarker([point.lat, point.lng], {
      radius: 7,
      color: '#0f172a',
      weight: 2,
      fillColor: style.color,
      fillOpacity: 0.9,
    });
    marker.bindPopup(buildPopup(point.name, [style.label + (point.open_24h ? ' · abierto 24h' : '')]));
    marker.bindTooltip(point.name);
    return marker;
  }

  function reportMarker(report) {
    const style = REPORT_STYLE[report.type] || { color: '#94a3b8', label: report.type };
    const marker = L.circleMarker([report.lat, report.lng], {
      radius: 6,
      color: '#0f172a',
      weight: 1,
      fillColor: style.color,
      fillOpacity: 0.85,
    });
    const extra = report.description ? [report.description] : [];
    marker.bindPopup(buildPopup(style.label, extra));
    return marker;
  }

  async function loadSafePoints() {
    const center = map.getCenter();
    try {
      const resp = await fetch(`/api/safe-points?lat=${center.lat}&lng=${center.lng}&radius=5000`);
      if (!resp.ok) return;
      const points = await resp.json();
      safePointsLayer.clearLayers();
      points.forEach((p) => safePointMarker(p).addTo(safePointsLayer));
    } catch (err) {
      console.error('No se pudieron cargar los puntos seguros', err);
    }
  }

  async function loadReports() {
    const bounds = map.getBounds();
    const params = new URLSearchParams({
      min_lat: bounds.getSouth(),
      max_lat: bounds.getNorth(),
      min_lng: bounds.getWest(),
      max_lng: bounds.getEast(),
    });
    try {
      const resp = await fetch(`/api/reports?${params.toString()}`);
      if (!resp.ok) return;
      const reports = await resp.json();
      reportsLayer.clearLayers();
      reports.forEach((r) => reportMarker(r).addTo(reportsLayer));
    } catch (err) {
      console.error('No se pudieron cargar los reportes', err);
    }
  }

  function addReportMarker(report) {
    reportMarker(report).addTo(reportsLayer);
  }

  function drawRoutes(rutas) {
    routesLayer.clearLayers();
    const polylines = [];
    rutas.forEach((ruta) => {
      const line = L.polyline(ruta.geometry, {
        color: isnColor(ruta.isn),
        weight: ruta.es_mas_segura ? 7 : 4,
        opacity: ruta.es_mas_segura ? 0.95 : 0.55,
        dashArray: ruta.es_mas_segura ? null : '6 6',
      });
      line.bindTooltip(`ISN ${ruta.isn}`);
      line.addTo(routesLayer);
      polylines.push(line);
    });
    if (polylines.length) {
      const group = L.featureGroup(polylines);
      // Deja libre la parte que tapa el panel inferior para que la ruta se vea completa
      const sheet = document.getElementById('bottom-sheet');
      const covered = sheet ? Math.max(0, window.innerHeight - sheet.getBoundingClientRect().top) : 0;
      const bottomPad = Math.min(covered, window.innerHeight * 0.6) + 40;
      map.fitBounds(group.getBounds(), { paddingTopLeft: [40, 110], paddingBottomRight: [40, bottomPad] });
    }
    return polylines;
  }

  function highlightRoute(polylines, index) {
    polylines.forEach((line, i) => {
      line.setStyle({ weight: i === index ? 8 : 4, opacity: i === index ? 1 : 0.35 });
      if (i === index) line.bringToFront();
    });
  }

  // ---------- Ubicación del usuario (punto azul) ----------
  let userMarker = null;

  function showUserLocation(loc) {
    if (userMarker) {
      userMarker.setLatLng([loc.lat, loc.lng]);
      return;
    }
    userMarker = L.circleMarker([loc.lat, loc.lng], {
      radius: 8,
      color: '#ffffff',
      weight: 3,
      fillColor: '#3b82f6',
      fillOpacity: 1,
      interactive: false,
    }).addTo(map);
  }

  function locateUser(options) {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocalización no disponible en este navegador'));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
          showUserLocation(loc);
          resolve(loc);
        },
        () => reject(new Error('No se pudo obtener tu ubicación')),
        Object.assign({ enableHighAccuracy: true, timeout: 8000 }, options)
      );
    });
  }

  // ---------- Marcadores de origen (A) y destino (B), arrastrables ----------
  const endpointMarkers = { origin: null, destination: null };
  const ENDPOINT_INFO = {
    origin: { letter: 'A', title: 'Origen (arrastra para moverlo)' },
    destination: { letter: 'B', title: 'Destino (arrastra para moverlo)' },
  };

  function setEndpointMarker(kind, loc, onMove) {
    let marker = endpointMarkers[kind];
    if (marker) {
      marker.setLatLng([loc.lat, loc.lng]);
      marker.off('dragend');
    } else {
      marker = L.marker([loc.lat, loc.lng], {
        icon: L.divIcon({
          className: 'endpoint-icon',
          html: `<div class="endpoint-pin ${kind}"><span>${ENDPOINT_INFO[kind].letter}</span></div>`,
          iconSize: [30, 30],
          iconAnchor: [15, 36],
        }),
        draggable: true,
        title: ENDPOINT_INFO[kind].title,
        zIndexOffset: 1000,
      }).addTo(endpointsLayer);
      endpointMarkers[kind] = marker;
    }
    if (onMove) {
      marker.on('dragend', () => {
        const p = marker.getLatLng();
        onMove({ lat: p.lat, lng: p.lng });
      });
    }
  }

  function clearEndpointMarker(kind) {
    if (!endpointMarkers[kind]) return;
    endpointsLayer.removeLayer(endpointMarkers[kind]);
    endpointMarkers[kind] = null;
  }

  // ---------- Elegir un punto tocando el mapa ----------
  let pickHandler = null;

  function cancelPick() {
    if (pickHandler) map.off('click', pickHandler);
    pickHandler = null;
    map.getContainer().classList.remove('pick-mode');
  }

  function startPick(onPick) {
    cancelPick();
    pickHandler = (ev) => {
      cancelPick();
      onPick({ lat: ev.latlng.lat, lng: ev.latlng.lng });
    };
    map.on('click', pickHandler);
    map.getContainer().classList.add('pick-mode');
  }

  map.on('moveend', () => {
    loadSafePoints();
    loadReports();
  });

  // Al abrir, centrar el mapa donde está el usuario (Bogotá queda solo como respaldo)
  const initialLocation = locateUser({ maximumAge: 60000 })
    .then((loc) => {
      if (!routesLayer.getLayers().length) map.setView([loc.lat, loc.lng], 15);
      return loc;
    })
    .catch(() => null);

  window.RutaMap = {
    map,
    loadSafePoints,
    loadReports,
    addReportMarker,
    drawRoutes,
    highlightRoute,
    locateUser,
    initialLocation,
    setEndpointMarker,
    clearEndpointMarker,
    startPick,
    cancelPick,
  };

  loadSafePoints();
  loadReports();
})();
