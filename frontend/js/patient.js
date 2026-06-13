// Patient Dashboard Logic — Auth-protected, with TTS + Translation

let currentPatient = null;
let currentData = null;
let currentTranslateText = '';
let currentTranslateReportId = null;
let ttsUtterance = null;

// ── Auth Guard ──────────────────────────────────────────────
function getToken() {
  return localStorage.getItem('healthai_token');
}

function authHeaders() {
  return { 'Authorization': `Bearer ${getToken()}`, 'Content-Type': 'application/json' };
}

async function authGet(path) {
  const res = await fetch(`${API}${path}`, { headers: authHeaders() });
  if (res.status === 401) { logout(); return null; }
  return res.json();
}

function logout() {
  localStorage.removeItem('healthai_token');
  localStorage.removeItem('healthai_patient');
  sessionStorage.removeItem('healthai_token');
  sessionStorage.removeItem('healthai_patient');
  window.location.href = '/pages/patient-login.html';
}

// ── Init ────────────────────────────────────────────────────
async function init() {
  const token = getToken();
  if (!token) { window.location.href = '/pages/patient-login.html'; return; }

  const data = await authGet('/api/patient/me');
  if (!data) return;

  currentPatient = data.patient;
  currentData = data;

  // Set preferred language
  const lang = currentPatient.preferredLanguage || 'English';
  document.getElementById('lang-select').value = lang;

  renderWelcome();
  renderStats();
  renderPatientInfo();
  renderNotifications();
  renderReports();
  renderScans();
  renderPrescriptions();
  renderAppointments();
  renderAIExplanation();
}

// ── Welcome ─────────────────────────────────────────────────
function renderWelcome() {
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening';
  document.getElementById('welcome-name').textContent = `${greeting}, ${currentPatient.name}`;
  document.getElementById('welcome-sub').textContent = `Patient ID: ${currentPatient.id} • ${currentPatient.condition}`;
}

// ── Stats ───────────────────────────────────────────────────
function renderStats() {
  const d = currentData;
  document.getElementById('stat-reports').textContent = d.reports.length;
  document.getElementById('stat-notifs').textContent = d.notifications.filter(n => !n.read).length;
  document.getElementById('stat-appointments').textContent = d.appointments.length;
  document.getElementById('stat-prescriptions').textContent = d.prescriptions.length;
}

// ── Patient Info ────────────────────────────────────────────
function renderPatientInfo() {
  const p = currentPatient;
  document.getElementById('patient-info').innerHTML = `
    <div class="card-header"><h3>📋 My Information</h3><span class="badge ${badgeClass(p.status)}">${p.status}</span></div>
    <div class="info-grid">
      <div class="info-item"><span class="info-label">Name</span><span class="info-value">${p.name}</span></div>
      <div class="info-item"><span class="info-label">Patient ID</span><span class="info-value">${p.id}</span></div>
      <div class="info-item"><span class="info-label">Age</span><span class="info-value">${p.age} years</span></div>
      <div class="info-item"><span class="info-label">Gender</span><span class="info-value">${p.gender}</span></div>
      <div class="info-item"><span class="info-label">Phone</span><span class="info-value">${p.phone || p.contact}</span></div>
      <div class="info-item"><span class="info-label">Language</span><span class="info-value">${p.preferredLanguage || 'English'}</span></div>
    </div>`;
}

// ── Notifications ───────────────────────────────────────────
function renderNotifications() {
  const notifs = currentData.notifications || [];
  const unread = notifs.filter(n => !n.read).length;
  document.getElementById('notif-count').textContent = unread;

  const container = document.getElementById('notifications-list');
  if (!notifs.length) {
    container.innerHTML = '<div class="empty-state"><div class="icon">🔔</div><p>No notifications yet</p></div>';
    return;
  }
  container.innerHTML = notifs.slice(0, 6).map(n => `
    <div class="notification-item ${n.read ? '' : 'unread'}">
      <div class="notification-dot ${severityDotClass(n.severity)}"></div>
      <div style="flex:1">
        <strong style="font-size:.875rem">${n.title}</strong>
        <p style="font-size:.82rem;color:var(--text-secondary);margin-top:4px">${n.message}</p>
        <span style="font-size:.7rem;color:var(--text-muted)">${timeAgo(n.created_at)}</span>
      </div>
      ${!n.read ? `<button class="btn btn-ghost btn-sm" onclick="markRead('${n.id}')">Mark read</button>` : ''}
    </div>`).join('');
}

// ── Reports ─────────────────────────────────────────────────
function renderReports() {
  const reports = currentData.reports || [];
  document.getElementById('reports-count').textContent = reports.length;

  const container = document.getElementById('reports-list');
  if (!reports.length) {
    container.innerHTML = '<div class="empty-state"><div class="icon">📄</div><p>No reports available</p></div>';
    return;
  }

  const typeIcons = { pdf: '📕', docx: '📘', image: '🖼️', scan: '🔬' };

  container.innerHTML = reports.map(r => `
    <div class="report-card" onclick="autoDownload('${r.id}')">
      <div class="report-card-icon">${typeIcons[r.reportType] || '📄'}</div>
      <div class="report-card-body">
        <h4>${r.reportName}</h4>
        <p class="report-meta">${r.doctor} • ${new Date(r.uploadDate).toLocaleDateString()}</p>
        <p class="report-summary">${r.summary ? r.summary.substring(0, 80) + '...' : 'View report details'}</p>
      </div>
      <div class="report-card-actions" onclick="event.stopPropagation()">
        <button class="btn btn-primary btn-sm" onclick="autoDownload('${r.id}')" title="Download">⬇ Download</button>
        <button class="btn btn-ghost btn-sm" onclick="openTranslate('${r.id}')" title="Translate">🌐</button>
        <button class="btn btn-ghost btn-sm" onclick="speakReport('${r.id}')" title="Listen">🔊</button>
        <a href="/pages/report-viewer.html?id=${r.id}" class="btn btn-ghost btn-sm" title="View">👁</a>
      </div>
      <div class="download-progress" id="dl-progress-${r.id}"></div>
    </div>`).join('');
}

// ── Prescriptions ───────────────────────────────────────────
function renderPrescriptions() {
  const prescs = currentData.full_prescriptions || [];
  const container = document.getElementById('prescriptions-list');
  if (!prescs.length) {
    container.innerHTML = '<div class="empty-state"><div class="icon">💊</div><p>No prescriptions</p></div>';
    return;
  }
  container.innerHTML = prescs.map(p => `
    <div class="prescription-item">
      <div class="presc-header">
        <h4>💊 ${p.diagnosis}</h4>
        <span class="badge ${p.status === 'active' ? 'badge-green' : 'badge-rose'}">${p.status}</span>
      </div>
      <div class="presc-content">
        <p><strong>Medicines:</strong></p>
        <p style="white-space: pre-wrap; font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 8px;">${p.medicines}</p>
        <p><strong>Instructions:</strong></p>
        <p style="white-space: pre-wrap; font-size: 0.9rem; color: var(--text-secondary);">${p.instructions || 'No special instructions'}</p>
      </div>
      <div class="presc-meta">
        <span>👨‍⚕️ Dr. ${p.doctor_name}</span>
        <span>📅 ${new Date(p.created_at).toLocaleDateString()}</span>
      </div>
      <div class="mt-2">
        <button class="btn btn-ghost btn-sm" onclick="downloadPrescription('${p.id}')">⬇ Download PDF</button>
      </div>
    </div>`).join('');
}

async function downloadPrescription(id) {
  window.open(`${API}/api/patient/download-prescription/${id}`, '_blank');
}

// ── Appointments ────────────────────────────────────────────
function renderAppointments() {
  const apts = currentData.appointments || [];
  const container = document.getElementById('appointments-list');
  if (!apts.length) {
    container.innerHTML = '<div class="empty-state"><div class="icon">📅</div><p>No appointments scheduled</p></div>';
    return;
  }
  container.innerHTML = apts.map(a => `
    <div class="appointment-item">
      <div class="apt-date-badge">
        <span class="apt-day">${new Date(a.date).getDate()}</span>
        <span class="apt-month">${new Date(a.date).toLocaleString('en', {month:'short'})}</span>
      </div>
      <div class="apt-details">
        <h4>${a.type} — ${a.specialty}</h4>
        <p>👨‍⚕️ ${a.doctor}</p>
        <p style="font-size:.8rem;color:var(--text-muted)">${a.notes || ''}</p>
      </div>
      <span class="badge ${a.status === 'scheduled' ? 'badge-cyan' : 'badge-green'}">${a.status}</span>
    </div>`).join('');
}

// ── Booking Appointments ────────────────────────────────────
async function openBookModal() {
  const modal = document.getElementById('book-modal');
  modal.classList.add('open');
  
  const select = document.getElementById('book-doctor');
  
  // Start loading state
  select.innerHTML = '<option value="">Loading doctors...</option>';
  select.disabled = true;

  try {
    console.log('Fetching doctors from /api/doctors/...');
    const res = await get('/api/doctors/');
    
    if (res && res.doctors && res.doctors.length > 0) {
      console.log('Doctors loaded:', res.doctors);
      select.innerHTML = '<option value="">Select a Doctor</option>' + res.doctors.map(d => {
        const spec = d.specialization || d.specialty || 'General Physician';
        return `<option value="${d.id}">Dr. ${d.name.replace('Dr. ', '')} — ${spec}</option>`;
      }).join('');
    } else if (res && res.doctors && res.doctors.length === 0) {
      select.innerHTML = '<option value="">No doctors available</option>';
    } else {
      throw new Error(res.error || 'Invalid response format');
    }
  } catch (e) {
    console.error('Failed to load doctors:', e);
    select.innerHTML = '<option value="">Failed to load doctors</option>';
    // Optional: show a toast or alert
    if (typeof showToast === 'function') {
      showToast('Error: Failed to load doctors', 'error');
    } else {
      alert('Failed to load doctors. Please try again.');
    }
  } finally {
    // End loading state
    select.disabled = false;
  }
}

function closeBookModal() {
  document.getElementById('book-modal').classList.remove('open');
}

async function submitBooking() {
  const doctor_id = document.getElementById('book-doctor').value;
  const appointment_date = document.getElementById('book-date').value;
  const time_slot = document.getElementById('book-time').value;
  const reason = document.getElementById('book-reason').value.trim();

  if (!doctor_id || !appointment_date || !reason) {
    alert('Please fill in all required fields (Doctor, Date, Reason).');
    return;
  }

  const btn = document.getElementById('book-btn');
  btn.disabled = true;
  btn.textContent = 'Sending Request...';

  try {
    const res = await post('/api/appointments/book', {
      patient_id: currentPatient.id,
      doctor_id,
      appointment_date,
      time_slot,
      reason
    });

    if (res.success) {
      alert('Appointment request sent successfully to staff!');
      closeBookModal();
      // Clear form
      document.getElementById('book-doctor').value = '';
      document.getElementById('book-date').value = '';
      document.getElementById('book-reason').value = '';
      // Refresh
      init();
    } else {
      alert('Failed to book appointment: ' + JSON.stringify(res));
    }
  } catch (e) {
    console.error('Booking error:', e);
    alert('An error occurred while booking. Please try again.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Send Request';
  }
}

// ── AI Explanation ───────────────────────────────────────────
function renderAIExplanation() {
  const images = currentData.imaging_records || [];
  const container = document.getElementById('ai-explanation');

  const analyzed = images.filter(i => i.ai_analysis);
  if (!analyzed.length) {
    container.innerHTML = '<div class="empty-state"><div class="icon">🧠</div><p>No AI analysis available yet. Your scans will appear here once analyzed.</p></div>';
    return;
  }

  container.innerHTML = analyzed.map(i => {
    const a = i.ai_analysis;
    const alert = a.patient_alert || a.patient_summary || 'Analysis in progress...';
    const severity = a.doctor_report?.severity || a.specialist_report?.severity || 'normal';
    return `
    <div class="ai-card">
      <div class="ai-card-header">
        <h4>${i.type} — ${i.id}</h4>
        <span class="badge ${badgeClass(severity)}">${severity}</span>
      </div>
      <div class="ai-card-body">
        <p class="ai-alert">${alert}</p>
      </div>
      <div class="ai-card-actions">
        <button class="btn btn-ghost btn-sm" onclick="openTranslateText(\`${alert.replace(/`/g, "'")}\`)">🌐 Translate</button>
        <button class="btn btn-ghost btn-sm" onclick="speakText(\`${alert.replace(/`/g, "'")}\`)">🔊 Listen</button>
      </div>
    </div>`;
  }).join('');
}

// ── Actions ─────────────────────────────────────────────────

async function markRead(notifId) {
  await post('/api/patients/notifications/read', { notification_id: notifId });
  // Update local
  const n = currentData.notifications.find(x => x.id === notifId);
  if (n) n.read = true;
  renderNotifications();
  renderStats();
}

async function autoDownload(reportId) {
  const progress = document.getElementById(`dl-progress-${reportId}`);
  if (progress) { progress.classList.add('active'); }

  try {
    const res = await fetch(`${API}/api/patient/reports/${reportId}/download`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${reportId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch(e) {
    console.error('Download error:', e);
  } finally {
    if (progress) { setTimeout(() => progress.classList.remove('active'), 1500); }
  }
}

// ── Translation ─────────────────────────────────────────────

function openTranslate(reportId) {
  const report = currentData.reports.find(r => r.id === reportId);
  if (!report) return;
  currentTranslateReportId = report.id;
  currentTranslateText = report.summary || report.reportName;
  document.getElementById('translate-original-text').textContent = currentTranslateText;
  document.getElementById('translate-original').style.display = 'block';
  document.getElementById('translate-result').style.display = 'none';
  document.getElementById('translate-translated').style.display = 'none';
  document.getElementById('translate-lang').value = document.getElementById('lang-select').value;
  document.getElementById('translate-modal').classList.add('open');
}

function openTranslateText(text) {
  currentTranslateReportId = null;
  currentTranslateText = text;
  document.getElementById('translate-original-text').textContent = text;
  document.getElementById('translate-original').style.display = 'block';
  document.getElementById('translate-result').style.display = 'none';
  document.getElementById('translate-translated').style.display = 'none';
  document.getElementById('translate-lang').value = document.getElementById('lang-select').value;
  document.getElementById('translate-modal').classList.add('open');
}

function closeTranslateModal() {
  document.getElementById('translate-modal').classList.remove('open');
}

async function doTranslate() {
  const lang = document.getElementById('translate-lang').value;
  const btn = document.getElementById('translate-btn');
  btn.textContent = '⏳ Translating...';
  btn.disabled = true;

  try {
    const res = await fetch(`${API}/api/reports/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        text: currentTranslateText, 
        target_language: lang,
        report_id: currentTranslateReportId 
      }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    // Replace displayed report text dynamically
    if (currentTranslateReportId && data.translated) {
      const report = currentData.reports.find(r => r.id === currentTranslateReportId);
      if (report) {
        report.summary = data.translated;
        renderReports();
      }
    }

    document.getElementById('translate-simplified-text').textContent = data.simplified;
    document.getElementById('translate-result').style.display = 'block';

    if (data.translated !== data.simplified) {
      document.getElementById('translate-translated-text').textContent = data.translated;
      document.getElementById('translate-translated').style.display = 'block';
    } else {
      document.getElementById('translate-translated').style.display = 'none';
    }
  } catch(e) {
    console.error('Translation error:', e);
    alert('Translation failed. Please retry.');
  } finally {
    btn.textContent = '🌐 Translate';
    btn.disabled = false;
  }
}

function speakTranslation() {
  const text = document.getElementById('translate-translated-text').textContent
    || document.getElementById('translate-simplified-text').textContent
    || currentTranslateText;
  speakText(text);
}

// ── TTS (Text-to-Speech) ────────────────────────────────────

function speakReport(reportId) {
  const report = currentData.reports.find(r => r.id === reportId);
  if (!report) return;
  speakText(`${report.reportName}. ${report.summary || ''}`);
}

function speakText(text) {
  if (!('speechSynthesis' in window)) { alert('Text-to-Speech not supported in this browser.'); return; }
  stopTTS();
  ttsUtterance = new SpeechSynthesisUtterance(text);
  ttsUtterance.rate = 0.9;
  ttsUtterance.pitch = 1;
  ttsUtterance.onend = () => { document.getElementById('tts-player').style.display = 'none'; };
  speechSynthesis.speak(ttsUtterance);
  document.getElementById('tts-player').style.display = 'block';
}

function pauseTTS() { speechSynthesis.pause(); }
function resumeTTS() { speechSynthesis.resume(); }
function stopTTS() {
  speechSynthesis.cancel();
  document.getElementById('tts-player').style.display = 'none';
}

// ── Language pref ───────────────────────────────────────────
async function saveLang() {
  const lang = document.getElementById('lang-select').value;
  if (currentPatient) currentPatient.preferredLanguage = lang;
  
  if (!currentData || !currentData.reports) return;

  for (let r of currentData.reports) {
    if (!r.original_summary) r.original_summary = r.summary || r.reportName;
    
    if (lang === 'English') {
      r.summary = r.original_summary;
    } else {
      try {
        const res = await fetch(`${API}/translate-report`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            report_text: r.original_summary,
            target_language: lang
          })
        });
        const data = await res.json();
        if (data.translated_text) {
          r.summary = data.translated_text;
        }
      } catch(e) {
        console.error('Auto-translate error:', e);
      }
    }
  }
  
  // Also translate AI explanations
  if (currentData.imaging_records) {
    for (let i of currentData.imaging_records) {
      if (i.ai_analysis && (i.ai_analysis.patient_alert || i.ai_analysis.original_alert)) {
        if (!i.ai_analysis.original_alert) i.ai_analysis.original_alert = i.ai_analysis.patient_alert;
        
        if (lang === 'English') {
          i.ai_analysis.patient_alert = i.ai_analysis.original_alert;
        } else {
          try {
            const res = await fetch(`${API}/translate-report`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                report_text: i.ai_analysis.original_alert,
                target_language: lang
              })
            });
            const data = await res.json();
            if (data.translated_text) {
              i.ai_analysis.patient_alert = data.translated_text;
            }
          } catch(e) {
            console.error('Auto-translate error:', e);
          }
        }
      }
    }
  }
  
  renderReports();
  renderAIExplanation();
}

// ── Medical Scans (DICOM) ───────────────────────────────────

async function renderScans() {
  const container = document.getElementById('scans-list');
  const countEl = document.getElementById('scans-count');
  if (!container) return;

  try {
    const res = await fetch(`${API}/api/patient/scans/${currentPatient.id}`);
    const data = await res.json();
    const scans = data.scans || [];
    if (countEl) countEl.textContent = scans.length;

    if (!scans.length) {
      container.innerHTML = '<div class="empty-state"><div class="icon">🔬</div><p>No medical scans available yet. Your doctor will upload scans here.</p></div>';
      return;
    }

    container.innerHTML = scans.map(s => {
      const title = s.scan_title || s.title || 'Untitled Scan';
      const date = new Date(s.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
      const size = s.file_size_formatted || formatScanBytes(s.file_size || 0);
      const modality = s.metadata?.modality || s.scan_type || '—';
      const bodyPart = s.body_part || s.metadata?.body_part || '—';

      return `
      <div class="scan-card">
        <div class="scan-card-icon">
          <span>${modality === 'MR' ? '🧠' : modality === 'CT' ? '🔄' : '🔬'}</span>
        </div>
        <div class="scan-card-body">
          <h4>${title}</h4>
          <div class="scan-card-meta">
            <span>👨‍⚕️ ${s.doctor_name || 'Unknown'}</span>
            <span>📅 ${date}</span>
            <span>🏷 ${s.scan_type}</span>
            <span>🦴 ${bodyPart}</span>
            <span>💾 ${size}</span>
          </div>
          ${s.notes ? `<p class="scan-notes">${s.notes}</p>` : ''}
        </div>
        <div class="scan-card-actions">
          <button class="btn btn-ghost btn-sm" onclick="viewScanMetadata('${s.id}')" title="View Metadata">📋 Metadata</button>
          <button class="btn btn-ghost btn-sm" onclick="viewScanPreview('${s.id}')" title="Preview Scan">👁 Preview</button>
          <button class="btn btn-primary btn-sm" onclick="downloadDicom('${s.id}', '${(s.file_name || 'scan.dcm').replace(/'/g, '')}')" title="Download DICOM">⬇ Download</button>
        </div>
      </div>`;
    }).join('');
  } catch (e) {
    console.error('Error loading scans:', e);
    container.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><p>Could not load scans</p></div>';
  }
}

function formatScanBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// ── Scan Metadata Modal ─────────────────────────────────────
async function viewScanMetadata(scanId) {
  const res = await fetch(`${API}/api/patient/scan-metadata/${scanId}`);
  const data = await res.json();
  if (!data.scan) return;

  const s = data.scan;
  const m = data.metadata || {};
  const title = s.scan_title || s.title || 'Untitled';

  document.getElementById('scan-metadata-content').innerHTML = `
    <div class="metadata-panel">
      <div class="metadata-header">
        <h4>🔬 ${title}</h4>
        <span class="badge ${badgeClass(s.status)}">${s.status}</span>
      </div>
      <div class="grid-2 mt-2">
        <div class="metadata-section">
          <h4 style="color:var(--accent-cyan);font-size:.85rem;margin-bottom:10px">📋 Scan Information</h4>
          <div class="info-grid">
            <div class="info-item"><span class="info-label">Study ID</span><span class="info-value">${s.study_id || '—'}</span></div>
            <div class="info-item"><span class="info-label">Scan Type</span><span class="info-value">${s.scan_type}</span></div>
            <div class="info-item"><span class="info-label">Body Part</span><span class="info-value">${s.body_part}</span></div>
            <div class="info-item"><span class="info-label">File Size</span><span class="info-value">${s.file_size_formatted || formatScanBytes(s.file_size || 0)}</span></div>
          </div>
        </div>
        <div class="metadata-section">
          <h4 style="color:var(--accent-purple);font-size:.85rem;margin-bottom:10px">🏥 DICOM Details</h4>
          <div class="info-grid">
            <div class="info-item"><span class="info-label">Patient Name</span><span class="info-value">${m.patient_name || '—'}</span></div>
            <div class="info-item"><span class="info-label">Study Date</span><span class="info-value">${m.study_date || '—'}</span></div>
            <div class="info-item"><span class="info-label">Modality</span><span class="info-value">${m.modality || '—'}</span></div>
            <div class="info-item"><span class="info-label">Dimensions</span><span class="info-value">${m.image_dimensions || '—'}</span></div>
          </div>
        </div>
      </div>
      <div class="mt-2 metadata-section">
        <h4 style="color:var(--accent-green);font-size:.85rem;margin-bottom:10px">🔧 Technical</h4>
        <div class="info-grid" style="grid-template-columns:1fr 1fr 1fr">
          <div class="info-item"><span class="info-label">Institution</span><span class="info-value">${m.institution || '—'}</span></div>
          <div class="info-item"><span class="info-label">Manufacturer</span><span class="info-value">${m.manufacturer || '—'}</span></div>
          <div class="info-item"><span class="info-label">Description</span><span class="info-value">${m.study_description || '—'}</span></div>
        </div>
      </div>
      ${s.notes ? `<div class="mt-2"><h4 style="color:var(--accent-amber);font-size:.85rem;margin-bottom:6px">📝 Doctor's Notes</h4><p style="color:var(--text-secondary);font-size:.9rem">${s.notes}</p></div>` : ''}
    </div>`;
  document.getElementById('scan-metadata-modal').classList.add('open');
}

function closeScanMetadata() {
  document.getElementById('scan-metadata-modal').classList.remove('open');
}

// ── Scan Preview Modal ──────────────────────────────────────
function viewScanPreview(scanId) {
  const viewer = document.getElementById('scan-viewer-content');
  viewer.innerHTML = `
    <div style="text-align:center;width:100%">
      <div class="spinner" style="margin:40px auto"></div>
      <p style="color:var(--text-muted);font-size:.85rem">Loading scan preview...</p>
    </div>`;
  document.getElementById('scan-viewer-modal').classList.add('open');

  const img = new Image();
  img.onload = () => {
    viewer.innerHTML = `
      <div style="text-align:center;width:100%">
        <img src="${API}/api/scan-preview/${scanId}" alt="Scan Preview" style="max-width:100%;max-height:500px;border-radius:var(--radius-md);border:1px solid var(--border-subtle)">
        <p style="color:var(--text-muted);font-size:.78rem;margin-top:12px">DICOM Scan Preview</p>
      </div>`;
  };
  img.onerror = () => {
    viewer.innerHTML = `
      <div style="text-align:center;padding:60px 20px">
        <div style="font-size:3rem;margin-bottom:16px;opacity:.5">🔬</div>
        <h4 style="color:var(--text-primary);margin-bottom:8px">Preview Unavailable</h4>
        <p style="color:var(--text-muted);font-size:.85rem">The scan preview could not be generated. You can still download the original DICOM file.</p>
      </div>`;
  };
  img.src = `${API}/api/scan-preview/${scanId}`;
}

function closeScanViewer() {
  document.getElementById('scan-viewer-modal').classList.remove('open');
}

// ── Download DICOM ──────────────────────────────────────────
async function downloadDicom(scanId, fileName) {
  try {
    const res = await fetch(`${API}/api/patient/download-dicom/${scanId}`);
    if (!res.ok) { alert('Download failed'); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName || `scan_${scanId}.dcm`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error('Download error:', e);
    alert('Error downloading scan: ' + e.message);
  }
}

// ── Boot ────────────────────────────────────────────────────
init();
