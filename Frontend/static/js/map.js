

const MapModule = (() => {
  const DEFAULT_LAT = 37.7749;
  const DEFAULT_LNG = -122.4194;
  const DEFAULT_ZOOM = 13;

  const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
  const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
  const createPinIcon = (status) => {
    let pinClass = 'pin-pending';
    let iconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';

    const normalized = (status || '').toLowerCase();
    if (normalized.includes('progress')) {
      pinClass = 'pin-progress';
      iconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>';
    } else if (normalized.includes('resolved')) {
      pinClass = 'pin-resolved';
      iconSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>';
    }

    return L.divIcon({
      className: 'flat-pin-wrapper',
      html: `<div class="custom-pin ${pinClass}">${iconSvg}</div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 13],
      popupAnchor: [0, -15]
    });
  };

  const initPickerMap = (elementId, latInputId, lngInputId) => {
    const container = document.getElementById(elementId);
    if (!container) return null;

    const latInput = document.getElementById(latInputId);
    const lngInput = document.getElementById(lngInputId);

    const map = L.map(elementId, {
      zoomControl: true,
      scrollWheelZoom: true,
      attributionControl: false
    }).setView([DEFAULT_LAT, DEFAULT_LNG], DEFAULT_ZOOM);

    L.tileLayer(TILE_URL, {
      attribution: '',
      maxZoom: 19
    }).addTo(map);

    let activeMarker = null;

    const updateInputs = (lat, lng) => {
      if (latInput) latInput.value = Number(lat).toFixed(6);
      if (lngInput) lngInput.value = Number(lng).toFixed(6);
    };

    const setLocation = (lat, lng, zoom = 15) => {
      lat = parseFloat(lat);
      lng = parseFloat(lng);
      if (isNaN(lat) || isNaN(lng)) return;

      if (activeMarker) {
        activeMarker.setLatLng([lat, lng]);
      } else {
        activeMarker = L.marker([lat, lng], {
          draggable: true,
          icon: createPinIcon('In Progress')
        }).addTo(map);

        activeMarker.on('dragend', (evt) => {
          const pos = evt.target.getLatLng();
          updateInputs(pos.lat, pos.lng);
        });
      }
      map.setView([lat, lng], zoom);
      updateInputs(lat, lng);
    };

    map.on('click', (e) => {
      const { lat, lng } = e.latlng;
      setLocation(lat, lng, map.getZoom());
    });
    setTimeout(() => {
      map.invalidateSize();
    }, 200);

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => map.setView([pos.coords.latitude, pos.coords.longitude], 14),
        () => {},
        { timeout: 5000 }
      );
    }

    return {
      map,
      setLocation,
      resetMarker: () => {
        if (activeMarker) {
          map.removeLayer(activeMarker);
          activeMarker = null;
        }
        if (latInput) latInput.value = '';
        if (lngInput) lngInput.value = '';
      }
    };
  };

  const initOverviewMap = (elementId, reports = [], highlightId = null) => {
    const container = document.getElementById(elementId);
    if (!container) return null;

    const map = L.map(elementId, {
      zoomControl: true,
      scrollWheelZoom: true,
      attributionControl: false
    }).setView([DEFAULT_LAT, DEFAULT_LNG], DEFAULT_ZOOM);

    L.tileLayer(TILE_URL, {
      attribution: '',
      maxZoom: 19
    }).addTo(map);

    const markersLayer = L.layerGroup().addTo(map);

    const renderMarkers = (items, targetId = highlightId) => {
      markersLayer.clearLayers();
      const bounds = [];
      let targetMarker = null;

      items.forEach(r => {
        if (r.latitude && r.longitude) {
          const marker = L.marker([r.latitude, r.longitude], {
            icon: createPinIcon(r.status)
          });
          const isTarget = targetId && String(r.id) === String(targetId);
          marker.bindPopup(`
            <div style="font-family:sans-serif; font-size:12px;">
              <strong style="display:block; margin-bottom:4px;">#${r.id}: ${r.title}</strong>
              <span style="color:#64748b;">${r.category}</span><br>
              <span style="font-weight:600; color:#065f46;">Status: ${r.status}</span>
              ${isTarget ? '<div style="margin-top:4px; font-weight:700; color:#065f46;">&bull; Your Reported Incident</div>' : ''}
            </div>
          `);
          marker.addTo(markersLayer);
          bounds.push([r.latitude, r.longitude]);

          if (isTarget) {
            targetMarker = marker;
          }
        }
      });

      if (targetMarker) {
        const pos = targetMarker.getLatLng();
        map.setView(pos, 15);
        setTimeout(() => targetMarker.openPopup(), 450);
      } else if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
      }
    };

    renderMarkers(reports, highlightId);

    setTimeout(() => {
      map.invalidateSize();
    }, 200);

    return {
      map,
      updateReports: (newReports) => renderMarkers(newReports)
    };
  };

  const initInspectionMap = (elementId, lat, lng, title) => {
    const container = document.getElementById(elementId);
    if (!container) return null;

    if (container._leaflet_map) {
      container._leaflet_map.remove();
    }

    const map = L.map(elementId, {
      zoomControl: false,
      attributionControl: false
    }).setView([lat || DEFAULT_LAT, lng || DEFAULT_LNG], 15);

    container._leaflet_map = map;

    L.tileLayer(TILE_URL, { maxZoom: 19 }).addTo(map);

    if (lat && lng) {
      L.marker([lat, lng], { icon: createPinIcon('In Progress') })
        .bindPopup(`<strong>${title || 'Incident Location'}</strong>`)
        .addTo(map);
    }

    setTimeout(() => map.invalidateSize(), 200);
    return map;
  };

  return { initPickerMap, initOverviewMap, initInspectionMap, createPinIcon };
})();
