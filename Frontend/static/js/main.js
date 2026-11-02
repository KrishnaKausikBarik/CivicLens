

const API_BASE_URL = window.location.origin;

async function readApiResponse(response) {
  const body = await response.text();
  let data;
  try {
    data = body ? JSON.parse(body) : {};
  } catch (_) {
    const message = body.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    throw new Error(message || `Server returned an unreadable response (${response.status}).`);
  }
  if (!response.ok) throw new Error(data.error || data.message || `Request failed (${response.status}).`);
  return data;
}

async function csrfFetch(url, options = {}) {
  const response = await fetch(`${API_BASE_URL}/api/csrf`, { credentials: 'same-origin' });
  const { csrf_token: csrfToken } = await readApiResponse(response);
  return fetch(url, {
    ...options,
    credentials: 'same-origin',
    headers: { ...(options.headers || {}), 'X-CSRF-Token': csrfToken }
  });
}

const INITIAL_DEMO_REPORTS = [
  {
    id: 101,
    title: "Major Pothole on Elm Street",
    category: "Roads & Footpaths",
    description: "Deep pothole causing vehicle tire damage near the traffic signal.",
    latitude: 37.7749,
    longitude: -122.4194,
    status: "Pending",
    created_at: "2026-10-28 09:15"
  },
  {
    id: 102,
    title: "Burst Water Main Flooding Sidewalk",
    category: "Water Supply",
    description: "Significant potable water flow erupting onto pedestrian pavement.",
    latitude: 37.7833,
    longitude: -122.4167,
    status: "In Progress",
    created_at: "2026-10-29 14:30"
  },
  {
    id: 103,
    title: "Overfilled Community Dumpsters",
    category: "Garbage & Waste",
    description: "Trash overflowing for over 3 days, spilling into driveway.",
    latitude: 37.7690,
    longitude: -122.4467,
    status: "Pending",
    created_at: "2026-10-30 08:00"
  },
  {
    id: 104,
    title: "Broken Streetlight Cluster",
    category: "Electricity",
    description: "Four sequential lamps are dark, creating dangerous pedestrian conditions.",
    latitude: 37.7600,
    longitude: -122.4200,
    status: "Resolved",
    created_at: "2026-10-25 18:45"
  },
  {
    id: 105,
    title: "Blocked Storm Drain Before Monsoon",
    category: "Drainage & Sewage",
    description: "Drain inlet clogged with solid debris and soil.",
    latitude: 37.7900,
    longitude: -122.4000,
    status: "In Progress",
    created_at: "2026-10-31 11:20"
  }
];

if (!localStorage.getItem('civiclens_mock_reports')) {
  localStorage.setItem('civiclens_mock_reports', JSON.stringify(INITIAL_DEMO_REPORTS));
}

const CivicAPI = {
  async getReports() {
    let serverReports = null;
    try {
      const response = await fetch(`${API_BASE_URL}/api/public/reports`, { credentials: 'same-origin' });
      if (response.ok) {
        serverReports = await response.json();
      }
    } catch (err) {
      console.warn('Backend server unreachable, using offline storage cache:', err.message);
    }

    const localReports = JSON.parse(localStorage.getItem('civiclens_mock_reports') || '[]');

    if (serverReports && Array.isArray(serverReports)) {
      const serverIds = new Set(serverReports.map(r => String(r.id)));
      const extraLocal = localReports.filter(r => !serverIds.has(String(r.id)));
      const combined = [...extraLocal, ...serverReports];
      localStorage.setItem('civiclens_mock_reports', JSON.stringify(combined));
      return combined;
    }

    return localReports;
  },

  async getCitizenReports() {
    const response = await fetch(`${API_BASE_URL}/api/reports`, { credentials: 'same-origin' });
    const reports = await readApiResponse(response);
    if (!Array.isArray(reports)) throw new Error('Unexpected response while loading complaints.');
    return reports;
  },

  async getAdminReports() {
    const response = await fetch(`${API_BASE_URL}/api/admin/reports`, { credentials: 'same-origin' });
    if (!response.ok) throw new Error('Administrator login required.');
    return response.json();
  },

  async createReport(reportData) {
    let createdReport = null;
    try {
      const response = await csrfFetch(`${API_BASE_URL}/api/reports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reportData)
      });
      const data = await response.json();
      if (!response.ok) {
        const error = new Error(data.error || 'Could not submit report.');
        error.status = response.status;
        throw error;
      }
      createdReport = data.report;
    } catch (err) {
      throw err;
    }
    const mine = JSON.parse(localStorage.getItem('civiclens_my_reports') || '[]');
    if (!mine.includes(String(createdReport.id))) {
      mine.unshift(String(createdReport.id));
      localStorage.setItem('civiclens_my_reports', JSON.stringify(mine));
    }
    return { success: true, report: createdReport };
  },

  async getStats() {
    const reports = await this.getReports();
    const total = reports.length;
    const pending = reports.filter(r => (r.status || '').toLowerCase() === 'pending').length;
    const in_progress = reports.filter(r => (r.status || '').toLowerCase() === 'in progress').length;
    const resolved = reports.filter(r => (r.status || '').toLowerCase() === 'resolved').length;
    const by_category = {};
    reports.forEach(r => {
      by_category[r.category] = (by_category[r.category] || 0) + 1;
    });
    return { total, pending, in_progress, resolved, by_category };
  },

  async updateReport(id, updateData) {
    let updatedReport = null;
    try {
      const response = await csrfFetch(`${API_BASE_URL}/api/reports/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(updateData)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not update report.');
      updatedReport = data.report;
    } catch (err) {
      throw err;
    }
    const items = JSON.parse(localStorage.getItem('civiclens_mock_reports') || '[]');
    const idx = items.findIndex(r => String(r.id) === String(id));
    if (idx !== -1) {
      items[idx] = { ...items[idx], ...updateData };
      if (updatedReport) {
        items[idx] = { ...items[idx], ...updatedReport };
      }
      localStorage.setItem('civiclens_mock_reports', JSON.stringify(items));
      if (!updatedReport) updatedReport = items[idx];
    }

    return { success: true, report: updatedReport };
  },

  async deleteReport(id) {
    const response = await csrfFetch(`${API_BASE_URL}/api/reports/${id}`, { method: 'DELETE' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not delete report.');
    return data;
  },

  async bulkDeleteReports(ids) {
    const response = await csrfFetch(`${API_BASE_URL}/api/reports/bulk-delete`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not delete reports.');
    return data;
  },

  async updateStatus(id, newStatus) {
    try {
      const headers = { 'Content-Type': 'application/json' };
      const response = await csrfFetch(`${API_BASE_URL}/api/admin/reports/${id}/status`, {
        method: 'PUT',
        headers: headers,
        credentials: 'same-origin',
        body: JSON.stringify({ status: newStatus })
      });
      if (!response.ok) throw new Error(`HTTP error ${response.status}`);
      return await response.json();
    } catch (err) {
      throw err;
    }
  }
};

function showToast(message, type = 'info') {
  const toast = document.getElementById('toastNotification');
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast-toast ${type} show`;
  setTimeout(() => { toast.className = 'toast-toast'; }, 3500);
}

function renderStatusBadge(status) {
  const norm = (status || 'pending').toLowerCase().replace(/\s+/g, '-');
  return `
    <span class="badge-status badge-${norm}">
      <span class="status-dot"></span>
      ${escapeHtml(status)}
    </span>
  `;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
function adaptNavigationLinks() {
  const isStaticEnv = window.location.protocol === 'file:' || !window.location.origin.includes(':5000');
  if (isStaticEnv) {
    document.querySelectorAll('a[href]').forEach(link => {
      const href = link.getAttribute('href');
      if (href === '/' || href === '/index.html') {
        link.setAttribute('href', 'index.html');
      } else if (href === '/dashboard' || href === '/dashboard.html') {
        link.setAttribute('href', 'dashboard.html');
      } else if (href === '/admin' || href === '/admin.html') {
        link.setAttribute('href', 'admin.html');
      }
    });
  }
}

let cachedReports = [];
function initIndexPage() {
  const form = document.getElementById('complaintForm');
  const pickerMap = MapModule.initPickerMap('pickerMap', 'latitude', 'longitude');
  let citizenAuthenticated = false;
  fetch(`${API_BASE_URL}/api/me`, { credentials: 'same-origin' }).then(r => r.json()).then(data => {
    if (data.user?.role === 'citizen') {
      citizenAuthenticated = true;
      const authLink = document.getElementById('citizenAuthBtn');
      if (authLink) { authLink.textContent = 'My Complaints'; authLink.href = '/citizen'; }
    }
  }).catch(() => {});

  async function loadRecentIssues() {
    const listContainer = document.getElementById('recentReportsList');
    if (!listContainer) return;

    try {
      const reports = await CivicAPI.getReports();
      const recent = reports.slice(0, 5);
      if (recent.length === 0) {
        listContainer.innerHTML = '<p class="text-center py-4" style="color:var(--color-text-muted);font-size:0.8rem;">No active reports recorded.</p>';
        return;
      }
      const myReports = JSON.parse(localStorage.getItem('civiclens_my_reports') || '[]');
      listContainer.innerHTML = recent.map(r => {
        const isMyReport = myReports.includes(String(r.id));
        return `
        <div class="activity-item">
          <div class="activity-meta">
            <span class="activity-cat">${escapeHtml(r.category)}</span>
            <div style="display:flex; align-items:center; gap:5px;">
              ${isMyReport ? `<button type="button" class="btn-edit-report" onclick="openEditComplaintModal(${r.id})" title="Edit your report"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Edit</button>` : ''}
              ${renderStatusBadge(r.status)}
            </div>
          </div>
          <div class="activity-title">${escapeHtml(r.title)}</div>
          <div class="activity-time">${escapeHtml(r.created_at || 'Recent')}</div>
        </div>
      `;
      }).join('');
    } catch (e) {
      listContainer.innerHTML = '<p class="text-center py-3" style="color:var(--color-text-muted);font-size:0.8rem;">Failed to fetch community log.</p>';
    }
  }
  const areaInput = document.getElementById('areaSearchInput');
  const areaBtn = document.getElementById('areaSearchBtn');
  const locationSuggestions = document.getElementById('locationSuggestions');
  let locationSearchTimer = null;
  let locationSearchController = null;
  let locationSearchVersion = 0;
  let locationFeatures = [];
  let activeLocationIndex = -1;

  const hideLocationSuggestions = () => {
    if (!locationSuggestions) return;
    locationSuggestions.hidden = true;
    locationSuggestions.replaceChildren();
    areaInput?.setAttribute('aria-expanded', 'false');
    areaInput?.removeAttribute('aria-activedescendant');
    areaInput?.closest('.area-search-wrapper')?.classList.remove('has-location-suggestions');
    activeLocationIndex = -1;
  };

  const showLocationSuggestionMessage = (message, loading = false) => {
    if (!locationSuggestions) return;
    locationSuggestions.innerHTML = loading
      ? `<div class="location-suggestions-message" role="status"><span class="location-suggestions-spinner" aria-hidden="true"></span>${escapeHtml(message)}</div>`
      : `<div class="location-suggestions-message" role="status">${escapeHtml(message)}</div>`;
    locationSuggestions.hidden = false;
    areaInput?.setAttribute('aria-expanded', 'true');
    areaInput?.closest('.area-search-wrapper')?.classList.add('has-location-suggestions');
  };

  const highlightLocationMatch = (value, query) => {
    const text = String(value || '');
    const start = text.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
    if (!query || start < 0) return escapeHtml(text);
    const end = start + query.length;
    return `${escapeHtml(text.slice(0, start))}<mark class="location-suggestion-match">${escapeHtml(text.slice(start, end))}</mark>${escapeHtml(text.slice(end))}`;
  };

  const describePhotonFeature = (feature) => {
    const properties = feature?.properties || {};
    const text = (value) => typeof value === 'string' ? value.trim() : '';
    const houseStreet = [text(properties.housenumber), text(properties.street)].filter(Boolean).join(' ');
    const city = text(properties.city) || text(properties.town) || text(properties.village) || text(properties.locality);
    const primary = text(properties.name) || houseStreet || text(properties.street) || city || text(properties.district) || text(properties.country) || 'Unnamed place';
    const details = [];
    [houseStreet, text(properties.district), city, text(properties.county), text(properties.state), text(properties.postcode), text(properties.country)].forEach((part) => {
      if (part && part.toLocaleLowerCase() !== primary.toLocaleLowerCase() && !details.some((existing) => existing.toLocaleLowerCase() === part.toLocaleLowerCase())) {
        details.push(part);
      }
    });
    return { primary, secondary: details.join(', '), address: [primary, details.join(', ')].filter(Boolean).join(', ') };
  };

  const setActiveLocationSuggestion = (index) => {
    const options = locationSuggestions?.querySelectorAll('[data-location-index]') || [];
    if (!options.length) return;
    activeLocationIndex = (index + options.length) % options.length;
    options.forEach((option, optionIndex) => {
      const selected = optionIndex === activeLocationIndex;
      option.classList.toggle('active', selected);
      option.setAttribute('aria-selected', String(selected));
    });
    const activeOption = options[activeLocationIndex];
    areaInput?.setAttribute('aria-activedescendant', activeOption.id);
    activeOption.scrollIntoView({ block: 'nearest' });
  };

  const renderLocationSuggestions = (features, query) => {
    locationFeatures = features;
    activeLocationIndex = -1;
    if (!features.length) {
      showLocationSuggestionMessage('No matching locations found. You can also click on the map to place the pin.');
      return;
    }

    locationSuggestions.innerHTML = features.map((feature, index) => {
      const place = describePhotonFeature(feature);
      return `<button type="button" class="location-suggestion" id="locationSuggestion${index}" role="option" aria-selected="false" data-location-index="${index}">
        <svg class="location-suggestion-pin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>
        <span class="location-suggestion-copy"><span class="location-suggestion-name">${highlightLocationMatch(place.primary, query)}</span>${place.secondary ? `<span class="location-suggestion-address">${highlightLocationMatch(place.secondary, query)}</span>` : ''}</span>
      </button>`;
    }).join('');
    locationSuggestions.hidden = false;
    areaInput?.setAttribute('aria-expanded', 'true');
    areaInput?.closest('.area-search-wrapper')?.classList.add('has-location-suggestions');
  };

  const selectLocationSuggestion = (index) => {
    const feature = locationFeatures[index];
    const coordinates = feature?.geometry?.coordinates;
    if (!Array.isArray(coordinates) || coordinates.length < 2) {
      showLocationSuggestionMessage('This location has no map coordinates. Please choose another result or click on the map.');
      return;
    }
    const place = describePhotonFeature(feature);
    areaInput.value = place.address;
    hideLocationSuggestions();
    if (pickerMap?.setLocation) pickerMap.setLocation(coordinates[1], coordinates[0], 16);
    showToast(`Location selected: ${place.primary}`, 'success');
  };

  const searchPhotonLocations = async (query, requestVersion) => {
    locationSearchController = new AbortController();
    showLocationSuggestionMessage('Searching locations…', true);
    try {
      const endpoint = `https://photon.komoot.io/api/?q=${encodeURIComponent(query)}&limit=6`;
      const response = await fetch(endpoint, {
        headers: { Accept: 'application/json' },
        signal: locationSearchController.signal
      });
      if (!response.ok) throw new Error('Location search request failed.');
      const data = await response.json();
      if (requestVersion !== locationSearchVersion || query !== areaInput.value.trim()) return;
      renderLocationSuggestions(Array.isArray(data.features) ? data.features : [], query);
    } catch (error) {
      if (error.name === 'AbortError' || requestVersion !== locationSearchVersion) return;
      showLocationSuggestionMessage('Location suggestions are unavailable. You can still choose a point on the map.');
    }
  };

  if (areaInput && locationSuggestions) {
    areaInput.addEventListener('input', () => {
      window.clearTimeout(locationSearchTimer);
      locationSearchController?.abort();
      locationSearchController = null;
      const requestVersion = ++locationSearchVersion;
      locationFeatures = [];
      hideLocationSuggestions();
      const query = areaInput.value.trim();
      if (query.length < 3) return;
      locationSearchTimer = window.setTimeout(() => searchPhotonLocations(query, requestVersion), 350);
    });

    areaInput.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown' && !locationSuggestions.hidden && locationFeatures.length) {
        event.preventDefault();
        setActiveLocationSuggestion(activeLocationIndex + 1);
      } else if (event.key === 'ArrowUp' && !locationSuggestions.hidden && locationFeatures.length) {
        event.preventDefault();
        setActiveLocationSuggestion(activeLocationIndex < 0 ? locationFeatures.length - 1 : activeLocationIndex - 1);
      } else if (event.key === 'Enter') {
        event.preventDefault();
        if (activeLocationIndex >= 0) selectLocationSuggestion(activeLocationIndex);
        else handleAreaSearch();
      } else if (event.key === 'Escape') {
        hideLocationSuggestions();
      }
    });

    locationSuggestions.addEventListener('click', (event) => {
      const option = event.target.closest('[data-location-index]');
      if (option) selectLocationSuggestion(Number(option.dataset.locationIndex));
    });

    locationSuggestions.addEventListener('mousedown', (event) => {
      if (event.target.closest('[data-location-index]')) event.preventDefault();
    });

    document.addEventListener('click', (event) => {
      if (!event.target.closest('.area-search-wrapper')) hideLocationSuggestions();
    });
  }

  async function handleAreaSearch() {
    const query = (areaInput ? areaInput.value : '').trim();
    if (!query) {
      showToast('Please enter an area, street, or landmark name.', 'info');
      areaInput?.focus();
      return;
    }

    const originalBtnHtml = areaBtn ? areaBtn.innerHTML : 'Locate Area';
    if (areaBtn) {
      areaBtn.disabled = true;
      areaBtn.innerHTML = '<span class="spinner" style="width:12px; height:12px; border-width:2px; vertical-align:middle; margin-right:4px;"></span> Searching...';
    }

    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`;
      const response = await fetch(url, { headers: { 'Accept': 'application/json' } });
      const results = await response.json();

      if (results && results.length > 0) {
        const place = results[0];
        const lat = parseFloat(place.lat);
        const lng = parseFloat(place.lon);
        if (pickerMap && pickerMap.setLocation) {
          pickerMap.setLocation(lat, lng, 15);
        }
        const shortName = place.display_name.split(',').slice(0, 2).join(',');
        showToast(`Area located: ${shortName}`, 'success');
      } else {
        showToast(`Could not find "${query}". Please click on the map to pin location.`, 'error');
      }
    } catch (err) {
      console.warn('Geocoding error:', err);
      showToast('Could not reach geocoding service. Please click directly on the map.', 'error');
    } finally {
      if (areaBtn) {
        areaBtn.disabled = false;
        areaBtn.innerHTML = originalBtnHtml;
      }
    }
  }

  if (areaBtn) {
    areaBtn.addEventListener('click', (e) => {
      e.preventDefault();
      handleAreaSearch();
    });
  }

  loadRecentIssues();

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('title').value.trim();
      const category = document.getElementById('category').value;
      const description = document.getElementById('description').value.trim();
      const latitude = parseFloat(document.getElementById('latitude').value);
      const longitude = parseFloat(document.getElementById('longitude').value);

      if (isNaN(latitude) || isNaN(longitude)) {
        showToast('Please select a point on the map to record location.', 'error');
        return;
      }

      if (!citizenAuthenticated) {
        setCitizenAuthMode('login');
        document.getElementById('citizenAuthModal')?.classList.add('open');
        document.getElementById('citizenLoginEmail')?.focus();
        return;
      }

      const submitBtn = document.getElementById('submitBtn');
      const spinner = document.getElementById('formSpinner');
      const btnText = submitBtn ? submitBtn.querySelector('.btn-text') : null;

      if (submitBtn) submitBtn.disabled = true;
      if (spinner) spinner.style.display = 'inline-block';
      if (btnText) btnText.style.display = 'none';

      try {
        const result = await CivicAPI.createReport({ title, category, description, latitude, longitude });
        const report = result.report;
        const formCard = document.querySelector('.form-card');
        const formBody = document.getElementById('complaintForm');

        if (formCard && formBody) {
          const dashboardUrl = (window.location.protocol === 'file:' || !window.location.origin.includes(':5000'))
            ? `dashboard.html?highlight=${report.id}`
            : `/dashboard.html?highlight=${report.id}`;

          formBody.style.display = 'none';

          const successDiv = document.createElement('div');
          successDiv.className = 'submission-success-card';
          successDiv.innerHTML = `
            <div style="display:flex; align-items:center; gap:0.75rem;">
              <span style="display:inline-flex; align-items:center; justify-content:center; width:36px; height:36px; background:#10b981; color:#fff; border-radius:50%; flex-shrink:0;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              </span>
              <div>
                <h3 style="font-size:1.1rem; color:#065f46; margin:0; font-weight:700;">Complaint Lodged Successfully!</h3>
                <p style="font-size:0.85rem; color:#047857; margin:2px 0 0 0;">Ticket <strong>#${report.id}</strong> &bull; Status: <span style="font-weight:600; color:#d97706;">Pending Verification</span></p>
              </div>
            </div>

            <div style="background:#fff; border:1px solid #d1fae5; border-radius:4px; padding:0.85rem; font-size:0.85rem;">
              <div style="font-weight:700; color:#0f172a; margin-bottom:0.25rem;">${escapeHtml(report.title)}</div>
              <div style="color:#64748b; font-size:0.8rem; margin-bottom:0.4rem;">${escapeHtml(report.category)} &bull; Coordinates: ${Number(report.latitude).toFixed(4)}, ${Number(report.longitude).toFixed(4)}</div>
              <p style="margin:0; color:#334155; font-size:0.82rem; line-height:1.4;">${escapeHtml(report.description)}</p>
            </div>

            <div style="font-size:0.85rem; color:#065f46; display:flex; align-items:center; gap:0.4rem;">
              <span class="spinner" style="width:14px; height:14px; border-width:2px;"></span>
              Opening in Public Dashboard in <strong id="redirectCountdown" style="font-weight:700; margin:0 2px;">2</strong>s...
            </div>

            <div style="display:flex; gap:0.75rem; flex-wrap:wrap; margin-top:0.25rem;">
              <a href="${dashboardUrl}" class="btn btn-primary" style="display:inline-flex; align-items:center; gap:0.4rem; padding:0.5rem 1rem;">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>
                View on Public Dashboard Now
              </a>
              <button type="button" id="submitAnotherBtn" class="btn btn-secondary" style="padding:0.5rem 0.85rem;">
                + Submit Another Report
              </button>
            </div>
          `;

          formCard.appendChild(successDiv);

          let secondsLeft = 2;
          const countdownEl = document.getElementById('redirectCountdown');
          const timer = setInterval(() => {
            secondsLeft -= 1;
            if (countdownEl) countdownEl.textContent = secondsLeft;
            if (secondsLeft <= 0) {
              clearInterval(timer);
              window.location.href = dashboardUrl;
            }
          }, 1000);

          document.getElementById('submitAnotherBtn')?.addEventListener('click', () => {
            clearInterval(timer);
            successDiv.remove();
            formBody.style.display = 'block';
            formBody.reset();
            if (pickerMap) pickerMap.resetMarker();
            loadRecentIssues();
          });
        }

        showToast(`Complaint #${report.id} lodged successfully.`, 'success');
        loadRecentIssues();

      } catch (err) {
        if (err.status === 401 || /citizen login required/i.test(err.message || '')) {
          citizenAuthenticated = false;
          setCitizenAuthMode('login');
          document.getElementById('citizenAuthModal')?.classList.add('open');
          document.getElementById('citizenLoginEmail')?.focus();
        } else {
          showToast(err.message || 'Submission error. Please retry.', 'error');
        }
      } finally {
        if (submitBtn) submitBtn.disabled = false;
        if (spinner) spinner.style.display = 'none';
        if (btnText) btnText.style.display = 'inline-flex';
      }
    });
  }
}
async function initDashboardPage() {
  const statTotal = document.getElementById('statTotal');
  const statPending = document.getElementById('statPending');
  const statInProgress = document.getElementById('statInProgress');
  const statResolved = document.getElementById('statResolved');
  const breakdownContainer = document.getElementById('categoryBreakdown');
  const tableBody = document.getElementById('dashboardTableBody');

  const searchInput = document.getElementById('dashboardSearchInput');
  const categoryFilter = document.getElementById('dashboardCategoryFilter');
  const statusFilter = document.getElementById('dashboardStatusFilter');
  const selectAllCheckbox = document.getElementById('selectAllCheckbox');
  const bulkBar = document.getElementById('bulkActionsBar');
  const selectedCountText = document.getElementById('selectedCountText');
  const urlParams = new URLSearchParams(window.location.search);
  const highlightId = urlParams.get('highlight') || localStorage.getItem('civiclens_latest_report_id');
  let myReports = JSON.parse(localStorage.getItem('civiclens_my_reports') || '[]');
  const selectedReportIds = new Set();

  try {
    const [reports, stats] = await Promise.all([CivicAPI.getReports(), CivicAPI.getStats()]);
    cachedReports = reports;

    function refreshDashboardMetrics() {
      const total = cachedReports.length;
      const pending = cachedReports.filter(r => (r.status || '').toLowerCase() === 'pending').length;
      const in_progress = cachedReports.filter(r => (r.status || '').toLowerCase() === 'in progress').length;
      const resolved = cachedReports.filter(r => (r.status || '').toLowerCase() === 'resolved').length;

      if (statTotal) statTotal.textContent = total;
      if (statPending) statPending.textContent = pending;
      if (statInProgress) statInProgress.textContent = in_progress;
      if (statResolved) statResolved.textContent = resolved;

      if (breakdownContainer) {
        const by_category = {};
        cachedReports.forEach(r => {
          by_category[r.category] = (by_category[r.category] || 0) + 1;
        });
        const cats = Object.entries(by_category);
        if (cats.length === 0) {
          breakdownContainer.innerHTML = '<p class="text-muted text-center py-3">No category data recorded.</p>';
        } else {
          const tot = total || 1;
          breakdownContainer.innerHTML = cats.map(([name, count]) => {
            const pct = Math.round((count / tot) * 100);
            return `
              <div class="category-row" style="margin-bottom:0.75rem;">
                <div class="flex-between" style="font-size:0.85rem; margin-bottom:0.25rem;">
                  <span>${escapeHtml(name)}</span>
                  <span style="font-weight:600;">${count} (${pct}%)</span>
                </div>
                <div style="background:var(--color-border); border-radius:4px; height:6px; overflow:hidden;">
                  <div style="background:var(--color-primary); width:${pct}%; height:100%;"></div>
                </div>
              </div>
            `;
          }).join('');
        }
      }
    }

    refreshDashboardMetrics();
    let overviewMapObj = null;
    if (MapModule.initOverviewMap) {
      overviewMapObj = MapModule.initOverviewMap('dashboardOverviewMap', cachedReports, highlightId);
      window.addEventListener('resize', () => {
        overviewMapObj?.map?.invalidateSize();
      });
    }

    function getFilteredReports() {
      const search = (searchInput?.value || '').toLowerCase();
      const cat = categoryFilter?.value || 'ALL';
      const status = statusFilter?.value || 'ALL';

      return cachedReports.filter(r => {
        const matchSearch = !search || 
          (r.title && r.title.toLowerCase().includes(search)) ||
          (r.description && r.description.toLowerCase().includes(search)) ||
          String(r.id).includes(search);
        const matchCat = (cat === 'ALL') || (r.category === cat);
        const matchStatus = (status === 'ALL') || (r.status === status);
        return matchSearch && matchCat && matchStatus;
      });
    }

    function updateBulkActionsBar() {
      const count = selectedReportIds.size;
      if (selectedCountText) {
        selectedCountText.textContent = `${count} complaint${count === 1 ? '' : 's'} selected`;
      }
      if (bulkBar) {
        bulkBar.style.display = count > 0 ? 'flex' : 'none';
      }

      const filtered = getFilteredReports();
      if (selectAllCheckbox) {
        if (filtered.length > 0 && filtered.every(r => selectedReportIds.has(Number(r.id)))) {
          selectAllCheckbox.checked = true;
          selectAllCheckbox.indeterminate = false;
        } else if (filtered.some(r => selectedReportIds.has(Number(r.id)))) {
          selectAllCheckbox.checked = false;
          selectAllCheckbox.indeterminate = true;
        } else {
          selectAllCheckbox.checked = false;
          selectAllCheckbox.indeterminate = false;
        }
      }
    }

    function renderTable() {
      if (!tableBody) return;
      const filtered = getFilteredReports();

      if (filtered.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4" style="color:var(--color-text-muted);">No reports match filter criteria.</td></tr>';
        updateBulkActionsBar();
        return;
      }

      tableBody.innerHTML = filtered.map(r => {
        const isMyReport = (highlightId && String(r.id) === String(highlightId)) || myReports.includes(String(r.id));
        const rowClass = isMyReport ? 'table-row-highlight' : '';
        const myBadge = isMyReport ? '<span class="badge-you">Your Report</span>' : '';
        const isChecked = selectedReportIds.has(Number(r.id));

        return `
        <tr class="${rowClass} ${isChecked ? 'row-selected' : ''}" id="reportRow-${r.id}">
          <td style="text-align: center;">
            <input type="checkbox" class="row-checkbox report-select-checkbox" data-id="${r.id}" ${isChecked ? 'checked' : ''} aria-label="Select complaint #${r.id}">
          </td>
          <td style="font-family:var(--font-mono); font-size:0.8rem; font-weight:700;">#${r.id}</td>
          <td>
            <div style="font-weight:600; display:flex; align-items:center; flex-wrap:wrap; gap:6px;">
              ${escapeHtml(r.title)}
              ${myBadge}
            </div>
            <div style="font-size:0.8rem; color:var(--color-text-sub); max-width:300px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
              ${escapeHtml(r.description)}
            </div>
          </td>
          <td>${escapeHtml(r.category)}</td>
          <td style="font-family:var(--font-mono); font-size:0.8rem;">${Number(r.latitude).toFixed(4)}, ${Number(r.longitude).toFixed(4)}</td>
          <td>${renderStatusBadge(r.status)}</td>
          <td style="font-size:0.8rem; color:var(--color-text-sub); white-space:nowrap;">
            ${escapeHtml(r.created_at || 'Recent')}
          </td>
          <td style="text-align: center;">
            <div class="row-action-buttons">
              <button type="button" class="action-icon-btn edit-action" onclick="openEditComplaintModal(${r.id})" title="Edit complaint #${r.id}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
              <button type="button" class="action-icon-btn delete-action" onclick="deleteComplaint(${r.id})" title="Delete complaint #${r.id}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  <line x1="10" y1="11" x2="10" y2="17"/>
                  <line x1="14" y1="11" x2="14" y2="17"/>
                </svg>
              </button>
            </div>
          </td>
        </tr>
      `;
      }).join('');

      updateBulkActionsBar();
      if (highlightId) {
        setTimeout(() => {
          const targetRow = document.getElementById(`reportRow-${highlightId}`);
          if (targetRow) {
            targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
            showToast(`Displaying your report #${highlightId} on the public dashboard.`, 'success');
          }
        }, 300);
      }
    }
    window.deleteComplaint = async function(reportId) {
      const confirmed = window.confirm(`Are you sure you want to permanently delete Incident Report #${reportId}?`);
      if (!confirmed) return;

      try {
        const res = await CivicAPI.deleteReport(reportId);
        if (res && res.success) {
          showToast(`Report #${reportId} deleted successfully.`, 'success');
          cachedReports = cachedReports.filter(r => String(r.id) !== String(reportId));
          selectedReportIds.delete(Number(reportId));

          myReports = myReports.filter(id => String(id) !== String(reportId));
          localStorage.setItem('civiclens_my_reports', JSON.stringify(myReports));

          refreshDashboardMetrics();
          renderTable();
          if (overviewMapObj?.renderMarkers) {
            overviewMapObj.renderMarkers(cachedReports);
          }
        } else {
          showToast(res.error || 'Failed to delete report.', 'error');
        }
      } catch (err) {
        showToast('Failed to delete report. Please try again.', 'error');
      }
    };
    window.bulkDeleteComplaints = async function() {
      const ids = Array.from(selectedReportIds);
      if (ids.length === 0) {
        showToast('Please select at least one report to delete.', 'info');
        return;
      }

      const confirmed = window.confirm(`Are you sure you want to permanently delete ${ids.length} selected complaint(s)? This action cannot be undone.`);
      if (!confirmed) return;

      try {
        let res = null;
        try {
          res = await CivicAPI.bulkDeleteReports(ids);
        } catch (e) {
          await Promise.all(ids.map(id => CivicAPI.deleteReport(id)));
          res = { success: true, deleted_count: ids.length };
        }

        if (res && res.success) {
          const count = res.deleted_count || ids.length;
          showToast(`${count} complaint(s) deleted successfully.`, 'success');

          const idSet = new Set(ids.map(String));
          cachedReports = cachedReports.filter(r => !idSet.has(String(r.id)));
          selectedReportIds.clear();

          myReports = myReports.filter(id => !idSet.has(String(id)));
          localStorage.setItem('civiclens_my_reports', JSON.stringify(myReports));

          refreshDashboardMetrics();
          renderTable();
          if (overviewMapObj?.renderMarkers) {
            overviewMapObj.renderMarkers(cachedReports);
          }
        } else {
          showToast(res.error || 'Failed to bulk delete reports.', 'error');
        }
      } catch (err) {
        showToast('Failed to bulk delete reports.', 'error');
      }
    };
    window.clearSelectedComplaints = function() {
      selectedReportIds.clear();
      renderTable();
    };
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener('change', (e) => {
        const checked = e.target.checked;
        const visibleReports = getFilteredReports();
        if (checked) {
          visibleReports.forEach(r => selectedReportIds.add(Number(r.id)));
        } else {
          visibleReports.forEach(r => selectedReportIds.delete(Number(r.id)));
        }
        renderTable();
      });
    }

    if (tableBody) {
      tableBody.addEventListener('change', (e) => {
        if (e.target && e.target.classList.contains('report-select-checkbox')) {
          const id = Number(e.target.dataset.id);
          if (e.target.checked) {
            selectedReportIds.add(id);
          } else {
            selectedReportIds.delete(id);
          }
          const row = document.getElementById(`reportRow-${id}`);
          if (row) {
            row.classList.toggle('row-selected', e.target.checked);
          }
          updateBulkActionsBar();
        }
      });
    }

    renderTable();

    searchInput?.addEventListener('input', () => {
      renderTable();
    });
    categoryFilter?.addEventListener('change', () => {
      renderTable();
    });
    statusFilter?.addEventListener('change', () => {
      renderTable();
    });

  } catch (err) {
    if (tableBody) tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4" style="color:var(--color-text-muted);">Failed to load dashboard data.</td></tr>';
  }
}
async function initAdminPage() {
  const statTotal = document.getElementById('adminStatTotal');
  const statPending = document.getElementById('adminStatPending');
  const statInProgress = document.getElementById('adminStatInProgress');
  const statResolved = document.getElementById('adminStatResolved');
  const tableBody = document.getElementById('adminTableBody');

  const searchInput = document.getElementById('adminSearchInput');
  const categoryFilter = document.getElementById('adminCategoryFilter');
  const statusFilter = document.getElementById('adminStatusFilter');

  try {
    cachedReports = await CivicAPI.getAdminReports();
    updateAdminStats(cachedReports);
    renderAdminTable();

    searchInput?.addEventListener('input', renderAdminTable);
    categoryFilter?.addEventListener('change', renderAdminTable);
    statusFilter?.addEventListener('change', renderAdminTable);
  } catch (err) {
    if (tableBody) tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4" style="color:var(--color-text-muted);">Failed to load admin reports.</td></tr>';
  }

  function updateAdminStats(reports) {
    const total = reports.length;
    const pending = reports.filter(r => (r.status || '').toLowerCase() === 'pending').length;
    const in_progress = reports.filter(r => (r.status || '').toLowerCase() === 'in progress').length;
    const resolved = reports.filter(r => (r.status || '').toLowerCase() === 'resolved').length;

    if (statTotal) statTotal.textContent = total;
    if (statPending) statPending.textContent = pending;
    if (statInProgress) statInProgress.textContent = in_progress;
    if (statResolved) statResolved.textContent = resolved;
  }

  function renderAdminTable() {
    if (!tableBody) return;
    const search = (searchInput?.value || '').toLowerCase();
    const cat = categoryFilter?.value || 'ALL';
    const status = statusFilter?.value || 'ALL';

    const filtered = cachedReports.filter(r => {
      const matchSearch = !search || 
        (r.title && r.title.toLowerCase().includes(search)) ||
        (r.description && r.description.toLowerCase().includes(search)) ||
        (r.full_name && r.full_name.toLowerCase().includes(search)) ||
        (r.user_email && r.user_email.toLowerCase().includes(search)) ||
        String(r.id).includes(search);
      const matchCat = (cat === 'ALL') || (r.category === cat);
      const matchStatus = (status === 'ALL') || (r.status === status);
      return matchSearch && matchCat && matchStatus;
    });

    if (filtered.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="9" class="text-center py-4" style="color:var(--color-text-muted);">No records found matching filters.</td></tr>';
      return;
    }

    tableBody.innerHTML = filtered.map(r => `
      <tr>
        <td style="font-family:var(--font-mono); font-size:0.8rem; font-weight:600;">#${r.id}</td>
        <td><button type="button" class="btn-link" onclick="openDetailModal(${r.id})">${escapeHtml(r.title)}</button></td>
        <td>${escapeHtml(r.category)}</td>
        <td>${escapeHtml(r.full_name || 'Legacy/Unknown')}</td>
        <td>${escapeHtml(r.user_email || 'Legacy/Unknown')}</td>
        <td>${escapeHtml(r.created_at || '—')}</td>
        <td style="font-family:var(--font-mono); font-size:0.8rem;">${Number(r.latitude).toFixed(4)}, ${Number(r.longitude).toFixed(4)}</td>
        <td>
          <select class="form-control" style="padding:0.3rem 0.5rem; font-size:0.8rem;" onchange="handleStatusChange(${r.id}, this.value)">
            <option value="Pending" ${r.status === 'Pending' ? 'selected' : ''}>Pending</option>
            <option value="In Progress" ${r.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
            <option value="Resolved" ${r.status === 'Resolved' ? 'selected' : ''}>Resolved</option>
          </select>
        </td>
        <td style="text-align: right;">
          <button type="button" class="btn btn-secondary btn-sm" onclick="openDetailModal(${r.id})">Inspect</button>
        </td>
      </tr>
    `).join('');
  }
}

async function initCitizenPage() {
  const tableBody = document.getElementById('citizenReportsBody');
  try {
    const [userResponse, reports] = await Promise.all([
      fetch(`${API_BASE_URL}/api/me`, { credentials: 'same-origin' }).then(r => r.json()),
      CivicAPI.getCitizenReports()
    ]);
    if (userResponse.user?.full_name) {
      document.getElementById('citizenWelcome').textContent = `Complaints from ${userResponse.user.full_name}`;
    }
    if (!reports.length) {
      tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4">You have not submitted any complaints yet.</td></tr>';
    } else {
      tableBody.innerHTML = reports.map(report => `
        <tr>
          <td>#${report.id}</td><td>${escapeHtml(report.title)}</td><td>${escapeHtml(report.category)}</td>
          <td>${escapeHtml(report.created_at)}</td>
          <td>${Number(report.latitude).toFixed(4)}, ${Number(report.longitude).toFixed(4)}</td>
          <td>${renderStatusBadge(report.status)}</td>
        </tr>`).join('');
    }
    if (MapModule.initOverviewMap) MapModule.initOverviewMap('citizenReportsMap', reports);
  } catch (error) {
    if (!tableBody) return;
    if (/citizen login required|citizen login expired/i.test(error.message || '')) {
      tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4">Your session has expired. <a href="/?citizen_login=1">Sign in again</a> to view your complaints.</td></tr>';
    } else {
      console.error('Unable to load the citizen complaint list.', error);
      tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4">Your complaints could not be loaded. Please refresh the page to try again.</td></tr>';
    }
  }
}
window.handleStatusChange = async function(id, newStatus) {
  try {
    await CivicAPI.updateStatus(id, newStatus);
    showToast(`Report #${id} updated to ${newStatus}.`, 'success');
    const target = cachedReports.find(r => String(r.id) === String(id));
    if (target) {
      target.status = newStatus;
      const statusCell = document.querySelector(`select[onchange="handleStatusChange(${id}, this.value)"]`);
      if (statusCell) statusCell.value = newStatus;
      const statTotal = document.getElementById('adminStatTotal');
      if (statTotal) {
        const pending = cachedReports.filter(r => (r.status || '').toLowerCase() === 'pending').length;
        const in_progress = cachedReports.filter(r => (r.status || '').toLowerCase() === 'in progress').length;
        const resolved = cachedReports.filter(r => (r.status || '').toLowerCase() === 'resolved').length;
        document.getElementById('adminStatPending').textContent = pending;
        document.getElementById('adminStatInProgress').textContent = in_progress;
        document.getElementById('adminStatResolved').textContent = resolved;
      }
    }
  } catch (e) {
    showToast('Failed to update report status.', 'error');
  }
};

window.openDetailModal = function(id) {
  const item = cachedReports.find(r => String(r.id) === String(id));
  if (!item) return;

  const modal = document.getElementById('detailModal');
  if (!modal) return;

  const titleEl = document.getElementById('modalTitle');
  const statusEl = document.getElementById('modalStatusBadge');
  const catEl = document.getElementById('modalCategory');
  const coordEl = document.getElementById('modalCoordinates');
  const dateEl = document.getElementById('modalDate');
  const descEl = document.getElementById('modalDescription');
  const submitter = document.getElementById('modalSubmitter');
  const userEmail = document.getElementById('modalUserEmail');
  const titleDetail = document.getElementById('modalComplaintTitle');

  if (titleEl) titleEl.textContent = `Report #${item.id}`;
  if (titleDetail) titleDetail.textContent = item.title;
  if (submitter) submitter.textContent = item.full_name || 'Legacy/Unknown';
  if (userEmail) userEmail.textContent = item.user_email || 'Legacy/Unknown';
  if (statusEl) statusEl.innerHTML = renderStatusBadge(item.status);
  if (catEl) catEl.textContent = item.category;
  if (coordEl) coordEl.textContent = `${item.latitude}, ${item.longitude}`;
  if (dateEl) dateEl.textContent = item.created_at || 'Recent';
  if (descEl) descEl.textContent = item.description;

  modal.classList.add('open');

  if (MapModule.initInspectionMap) {
    MapModule.initInspectionMap('modalMap', item.latitude, item.longitude, item.title);
  }
};

window.closeDetailModal = function() {
  document.getElementById('detailModal')?.classList.remove('open');
};

window.closeLoginModal = function() {
  document.getElementById('loginModal')?.classList.remove('open');
};

document.getElementById('forgotPasswordToggle')?.addEventListener('click', (event) => {
  const help = document.getElementById('forgotPasswordHelp');
  if (!help) return;
  help.hidden = !help.hidden;
  event.currentTarget.setAttribute('aria-expanded', String(!help.hidden));
});

window.handleLoginSubmit = async function(e) {
  e.preventDefault();
  const emailInput = document.getElementById('loginUser');
  const passInput = document.getElementById('loginPass');
  const username = emailInput ? emailInput.value : '';
  const password = passInput ? passInput.value : '';
  const error = document.getElementById('loginError');
  if (error) error.textContent = '';

  try {
    const res = await csrfFetch(`${API_BASE_URL}/api/auth/admin-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      window.location.assign('/admin');
      return;
    }
    if (error) error.textContent = data.error || 'Invalid username or password';
  } catch (_) {
    if (error) error.textContent = 'Unable to sign in. Please try again.';
  }
};

document.getElementById('authBtn')?.addEventListener('click', (e) => {
  e.preventDefault();
  document.getElementById('loginModal')?.classList.add('open');
});

window.closeCitizenAuthModal = function() {
  document.getElementById('citizenAuthModal')?.classList.remove('open');
};

function setCitizenAuthMode(mode) {
  const registering = mode === 'register';
  const recovering = mode === 'forgot';
  document.getElementById('citizenLoginForm').style.display = registering || recovering ? 'none' : '';
  document.getElementById('citizenRegisterForm').style.display = registering ? '' : 'none';
  document.getElementById('citizenForgotPasswordForm').style.display = recovering ? '' : 'none';
  document.getElementById('citizenAuthTitle').textContent = registering
    ? 'Create Citizen Account'
    : recovering ? 'Forgot Your Password?' : 'Citizen Login';
  if (recovering) {
    document.getElementById('forgotPasswordEmail').value = document.getElementById('citizenLoginEmail').value;
    document.getElementById('forgotPasswordMessage').textContent = '';
    document.getElementById('forgotPasswordMessage').style.color = '';
  }
}

document.getElementById('citizenAuthBtn')?.addEventListener('click', e => {
  if (e.currentTarget.getAttribute('href') === '/citizen') return;
  e.preventDefault();
  setCitizenAuthMode('login');
  document.getElementById('citizenAuthModal')?.classList.add('open');
});
document.getElementById('openCitizenLogin')?.addEventListener('click', e => {
  e.preventDefault();
  setCitizenAuthMode('login');
  document.getElementById('citizenAuthModal')?.classList.add('open');
});
document.getElementById('showRegister')?.addEventListener('click', () => setCitizenAuthMode('register'));
document.getElementById('showLogin')?.addEventListener('click', () => setCitizenAuthMode('login'));
document.getElementById('citizenForgotPasswordToggle')?.addEventListener('click', () => setCitizenAuthMode('forgot'));
document.getElementById('forgotPasswordBackToLogin')?.addEventListener('click', () => setCitizenAuthMode('login'));

document.getElementById('citizenForgotPasswordForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = document.getElementById('forgotPasswordMessage');
  message.textContent = '';
  message.style.color = '';
  try {
    const response = await csrfFetch(`${API_BASE_URL}/api/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: document.getElementById('forgotPasswordEmail').value })
    });
    const data = await readApiResponse(response);
    message.textContent = data.message;
    message.style.color = '#047857';
  } catch (error) {
    message.textContent = error.message || 'Unable to send the reset link. Please try again.';
  }
});

document.getElementById('citizenLoginForm')?.addEventListener('submit', async e => {
  e.preventDefault();
  const error = document.getElementById('citizenLoginError');
  error.textContent = '';
  error.style.color = '';
  try {
    const response = await csrfFetch(`${API_BASE_URL}/api/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: document.getElementById('citizenLoginEmail').value, password: document.getElementById('citizenLoginPassword').value })
    });
    const data = await readApiResponse(response);
    if (!response.ok) throw new Error(data.error || 'Unable to log in.');
    window.location.assign('/citizen');
  } catch (err) { error.textContent = err.message; }
});

document.getElementById('citizenRegisterForm')?.addEventListener('submit', async e => {
  e.preventDefault();
  const error = document.getElementById('citizenRegisterError');
  error.textContent = '';
  const password = document.getElementById('registerPassword').value;
  if (password !== document.getElementById('registerConfirmPassword').value) {
    error.textContent = 'Passwords do not match.';
    return;
  }
  try {
    const response = await csrfFetch(`${API_BASE_URL}/api/register`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: document.getElementById('registerFullName').value,
        email: document.getElementById('registerEmail').value,
        password,
        confirm_password: document.getElementById('registerConfirmPassword').value
      })
    });
    const data = await readApiResponse(response);
    if (!response.ok) throw new Error(data.error || 'Could not create account.');
    document.getElementById('citizenLoginEmail').value = document.getElementById('registerEmail').value;
    document.getElementById('citizenRegisterForm').reset();
    setCitizenAuthMode('login');
    document.getElementById('citizenLoginError').textContent = 'Account created. Please log in.';
    document.getElementById('citizenLoginError').style.color = '#047857';
  } catch (err) { error.textContent = err.message; }
});

function initPasswordReset() {
  const resetForm = document.getElementById('resetPasswordForm');
  const status = document.getElementById('resetPasswordStatus');
  const done = document.getElementById('resetPasswordDone');
  const resetUrl = new URL(window.location.href);
  const resetToken = new URLSearchParams(resetUrl.hash.slice(1)).get('token') || '';
  window.history.replaceState(null, '', '/reset-password');

  document.querySelectorAll('[data-toggle-password]').forEach((button) => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.togglePassword);
      const showing = input.type === 'password';
      input.type = showing ? 'text' : 'password';
      button.textContent = showing ? 'Hide password' : 'Show password';
      button.setAttribute('aria-pressed', String(showing));
    });
  });

  const showResetError = (message) => {
    status.textContent = message;
    status.classList.remove('reset-success');
    status.classList.add('form-error');
  };

  (async () => {
    if (!resetToken) {
      showResetError('This reset link is invalid or has expired.');
      return;
    }
    try {
      const response = await csrfFetch(`${API_BASE_URL}/api/auth/validate-reset-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: resetToken })
      });
      await readApiResponse(response);
      status.hidden = true;
      resetForm.hidden = false;
    } catch (error) {
      showResetError(error.message || 'This reset link is invalid or has expired.');
    }
  })();

  resetForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const password = document.getElementById('newPassword').value;
    const confirmation = document.getElementById('confirmNewPassword').value;
    status.hidden = false;
    status.classList.remove('reset-success', 'form-error');
    if (password.length < 8 || password.length > 256) {
      status.textContent = 'Password must be between 8 and 256 characters.';
      status.classList.add('form-error');
      return;
    }
    if (password !== confirmation) {
      status.textContent = 'Passwords do not match.';
      status.classList.add('form-error');
      return;
    }
    try {
      const response = await csrfFetch(`${API_BASE_URL}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: resetToken, password, confirm_password: confirmation })
      });
      const data = await readApiResponse(response);
      resetForm.hidden = true;
      status.textContent = data.message;
      status.classList.remove('form-error');
      status.classList.add('reset-success');
      done.hidden = false;
      window.setTimeout(() => window.location.assign('/?citizen_login=1'), 2500);
    } catch (error) {
      status.textContent = error.message || 'Unable to reset your password. Please try again.';
      status.classList.add('form-error');
    }
  });
}

if (document.body.dataset.resetMode === 'true' || document.body.dataset.page === 'reset-password') {
  initPasswordReset();
}

if (new URLSearchParams(window.location.search).has('citizen_login')) {
  setCitizenAuthMode('login');
  document.getElementById('citizenAuthModal')?.classList.add('open');
}

if (new URLSearchParams(window.location.search).has('admin_login')) {
  document.getElementById('loginModal')?.classList.add('open');
}

document.getElementById('adminLogoutBtn')?.addEventListener('click', async () => {
  await csrfFetch(`${API_BASE_URL}/api/logout`, { method: 'POST' });
  window.location.assign('/');
});

document.getElementById('citizenLogoutBtn')?.addEventListener('click', async () => {
  await csrfFetch(`${API_BASE_URL}/api/logout`, { method: 'POST' });
  window.location.assign('/');
});
function initMobileNavigation() {
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const navLinks = document.getElementById('navLinks') || document.querySelector('.nav-links');
  let navBackdrop = document.getElementById('navBackdrop');

  if (mobileMenuBtn && navLinks) {
    if (!navBackdrop) {
      navBackdrop = document.createElement('div');
      navBackdrop.id = 'navBackdrop';
      navBackdrop.className = 'nav-backdrop';
      document.body.appendChild(navBackdrop);
    }

    const closeNav = () => {
      navLinks.classList.remove('open');
      mobileMenuBtn.classList.remove('active');
      mobileMenuBtn.setAttribute('aria-expanded', 'false');
      navBackdrop?.classList.remove('open');
    };

    const openNav = () => {
      navLinks.classList.add('open');
      mobileMenuBtn.classList.add('active');
      mobileMenuBtn.setAttribute('aria-expanded', 'true');
      navBackdrop?.classList.add('open');
    };

    mobileMenuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (navLinks.classList.contains('open')) {
        closeNav();
      } else {
        openNav();
      }
    });

    navBackdrop.addEventListener('click', closeNav);
    navLinks.querySelectorAll('.nav-link').forEach((link) => {
      link.addEventListener('click', closeNav);
    });
    document.addEventListener('click', (e) => {
      if (!navLinks.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
        if (navLinks.classList.contains('open')) {
          closeNav();
        }
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && navLinks.classList.contains('open')) {
        closeNav();
      }
    });
    window.addEventListener('resize', () => {
      if (window.innerWidth > 768 && navLinks.classList.contains('open')) {
        closeNav();
      }
    });
  }
  const menuToggle = document.getElementById('menuToggle');
  const adminSidebar = document.getElementById('adminSidebar');
  const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');

  const closeSidebar = () => {
    adminSidebar?.classList.remove('open');
    sidebarBackdrop?.classList.remove('open');
  };

  const openSidebar = () => {
    adminSidebar?.classList.add('open');
    sidebarBackdrop?.classList.add('open');
  };

  if (menuToggle && adminSidebar) {
    menuToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      if (adminSidebar.classList.contains('open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });

    sidebarCloseBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      closeSidebar();
    });

    sidebarBackdrop?.addEventListener('click', closeSidebar);

    adminSidebar.querySelectorAll('.sidebar-item').forEach((item) => {
      item.addEventListener('click', () => {
        if (window.innerWidth <= 960) {
          closeSidebar();
        }
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && adminSidebar.classList.contains('open')) {
        closeSidebar();
      }
    });
  }
}
window.openEditComplaintModal = async function(reportId) {
  const modal = document.getElementById('editComplaintModal');
  if (!modal) return;

  let report = (cachedReports || []).find(r => String(r.id) === String(reportId));
  if (!report) {
    const all = await CivicAPI.getReports();
    report = all.find(r => String(r.id) === String(reportId));
  }

  if (!report) {
    showToast('Could not find complaint #' + reportId, 'error');
    return;
  }

  const idInput = document.getElementById('editReportId');
  if (idInput) idInput.value = report.id;

  const modalIdSpan = document.getElementById('editModalReportId');
  if (modalIdSpan) modalIdSpan.textContent = report.id;

  const titleInput = document.getElementById('editTitle');
  if (titleInput) titleInput.value = report.title || '';

  const catInput = document.getElementById('editCategory');
  if (catInput) catInput.value = report.category || 'Roads & Footpaths';

  const descInput = document.getElementById('editDescription');
  if (descInput) descInput.value = report.description || '';

  const latInput = document.getElementById('editLatitude');
  if (latInput) latInput.value = report.latitude || '';

  const lngInput = document.getElementById('editLongitude');
  if (lngInput) lngInput.value = report.longitude || '';

  modal.classList.add('open');
};

window.closeEditModal = function() {
  document.getElementById('editComplaintModal')?.classList.remove('open');
};

function initEditComplaintForm() {
  const editForm = document.getElementById('editComplaintForm');
  if (!editForm) return;

  editForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('editReportId')?.value;
    const title = document.getElementById('editTitle')?.value.trim();
    const category = document.getElementById('editCategory')?.value;
    const description = document.getElementById('editDescription')?.value.trim();
    const latitude = parseFloat(document.getElementById('editLatitude')?.value);
    const longitude = parseFloat(document.getElementById('editLongitude')?.value);

    if (!id || !title || !description || isNaN(latitude) || isNaN(longitude)) {
      showToast('Please fill in all required fields.', 'error');
      return;
    }

    const saveBtn = document.getElementById('saveEditBtn');
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.innerHTML = '<span class="spinner" style="width:14px; height:14px; border-width:2px; vertical-align:middle; margin-right:4px;"></span> Saving...';
    }

    try {
      const res = await CivicAPI.updateReport(id, {
        title, category, description, latitude, longitude
      });

      if (res && res.success) {
        showToast(`Complaint #${id} updated successfully!`, 'success');
        window.closeEditModal();
        cachedReports = await CivicAPI.getReports();
        const page = document.body.dataset.page;
        if (page === 'dashboard') {
          const searchInput = document.getElementById('dashboardSearchInput');
          if (searchInput) searchInput.dispatchEvent(new Event('input'));
        } else if (page === 'index') {
          const listContainer = document.getElementById('recentIssuesList');
          if (listContainer) {
            const recent = cachedReports.slice(0, 5);
            const myReports = JSON.parse(localStorage.getItem('civiclens_my_reports') || '[]');
            listContainer.innerHTML = recent.map(r => {
              const isMyReport = myReports.includes(String(r.id));
              return `
              <div class="activity-item">
                <div class="activity-meta">
                  <span class="activity-cat">${escapeHtml(r.category)}</span>
                  <div style="display:flex; align-items:center; gap:5px;">
                    ${isMyReport ? `<button type="button" class="btn-edit-report" onclick="openEditComplaintModal(${r.id})" title="Edit your report"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Edit</button>` : ''}
                    ${renderStatusBadge(r.status)}
                  </div>
                </div>
                <div class="activity-title">${escapeHtml(r.title)}</div>
                <div class="activity-time">${escapeHtml(r.created_at || 'Recent')}</div>
              </div>
            `;
            }).join('');
          }
        }
      } else {
        showToast('Failed to update complaint.', 'error');
      }
    } catch (err) {
      showToast('Error saving updates: ' + err.message, 'error');
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<span class="btn-text"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg><span>Save Changes</span></span>';
      }
    }
  });
  document.getElementById('editComplaintModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'editComplaintModal') {
      window.closeEditModal();
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initEditComplaintForm();
  adaptNavigationLinks();
  initMobileNavigation();

  const page = document.body.dataset.page;
  if (page === 'index') {
    initIndexPage();
  } else if (page === 'dashboard') {
    initDashboardPage();
  } else if (page === 'admin') {
    initAdminPage();
  } else if (page === 'citizen') {
    initCitizenPage();
  }
});
