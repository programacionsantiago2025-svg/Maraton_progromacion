// map.js - inicialización del mapa Leaflet y capas de RutaSegura
(function () {
  const DEFAULT_CENTER = [4.6097, -74.0817]; // Bogotá
  const DEFAULT_ZOOM = 13;

  const map = L.map('map', {
    center: DEFAULT_CENTER,
    zoom: DEFAULT_ZOOM,
    zoomControl: true,
    attributionControl: false,
  });

  // Arriba a la derecha: abajo la taparía el panel, y la atribución es obligatoria (ODbL)
  L.control.attribution({ position: 'topright' }).addTo(map);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map);

  const safePointsLayer = L.layerGroup().addTo(map);
  const reportsLayer = L.layerGroup().addTo(map);
  const routesLayer = L.layerGroup().addTo(map);

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
      map.fitBounds(group.getBounds(), { padding: [40, 40] });
    }
    return polylines;
  }

  function highlightRoute(polylines, index) {
    polylines.forEach((line, i) => {
      line.setStyle({ weight: i === index ? 8 : 4, opacity: i === index ? 1 : 0.35 });
      if (i === index) line.bringToFront();
    });
  }

  function locateUser() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocalización no disponible en este navegador'));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => reject(new Error('No se pudo obtener tu ubicación')),
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });
  }

  map.on('moveend', () => {
    loadSafePoints();
    loadReports();
  });

  window.RutaMap = {
    map,
    loadSafePoints,
    loadReports,
    addReportMarker,
    drawRoutes,
    highlightRoute,
    locateUser,
  };

  loadSafePoints();
  loadReports();
})();
