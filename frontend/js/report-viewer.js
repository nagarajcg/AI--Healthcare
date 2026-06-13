// Report Viewer Logic

let reportData = null;

async function init() {
  const params = new URLSearchParams(window.location.search);
  const reportId = params.get('id');
  if (!reportId) { document.getElementById('report-preview').innerHTML = '<p style="color:var(--accent-rose)">No report ID specified.</p>'; return; }

  try {
    const res = await fetch(`${API}/api/patient/report-detail/${reportId}`);
    const data = await res.json();
    if (data.error) throw new Error(data.detail || data.error);
    reportData = data;
    renderReport();
  } catch(e) {
    document.getElementById('report-preview').innerHTML = `<p style="color:var(--accent-rose)">Error: ${e.message}</p>`;
  }
}

function renderReport() {
  const r = reportData.report;
  const p = reportData.patient;
  const img = reportData.imaging;

  document.getElementById('report-title').textContent = r.reportName;
  document.getElementById('report-subtitle').textContent = `${r.doctor} • ${new Date(r.uploadDate).toLocaleDateString()}`;
  document.getElementById('action-bar').style.display = 'flex';

  // Preview
  document.getElementById('report-preview').innerHTML = `
    <div class="report-preview-doc">
      <div class="report-preview-header">
        <h2>🧬 HealthAI</h2>
        <p>AI Healthcare Imaging Data Regulator</p>
      </div>
      <h3>${r.reportName}</h3>
      <div class="report-preview-meta">
        <div><strong>Patient:</strong> ${p.name || 'N/A'}</div>
        <div><strong>Patient ID:</strong> ${r.patient_id}</div>
        <div><strong>Age/Gender:</strong> ${p.age || 'N/A'} / ${p.gender || 'N/A'}</div>
        <div><strong>Doctor:</strong> ${r.doctor}</div>
        <div><strong>Date:</strong> ${new Date(r.uploadDate).toLocaleDateString()}</div>
        <div><strong>Type:</strong> ${r.reportType.toUpperCase()}</div>
      </div>
      <hr style="border-color:var(--border-subtle);margin:16px 0">
      <h4 style="color:var(--accent-cyan);margin-bottom:8px">Clinical Summary</h4>
      <p style="line-height:1.8;color:var(--text-secondary)">${r.summary || 'No summary available.'}</p>
      ${img ? `
        <hr style="border-color:var(--border-subtle);margin:16px 0">
        <h4 style="color:var(--accent-cyan);margin-bottom:8px">Imaging Study</h4>
        <p style="color:var(--text-secondary)">${img.type} (${img.id}) — Status: ${img.status.toUpperCase()}</p>
      ` : ''}
    </div>`;

  // Metadata
  document.getElementById('report-meta').innerHTML = `
    <div class="info-grid">
      <div class="info-item"><span class="info-label">Report ID</span><span class="info-value">${r.id}</span></div>
      <div class="info-item"><span class="info-label">Patient</span><span class="info-value">${p.name || 'N/A'}</span></div>
      <div class="info-item"><span class="info-label">Doctor</span><span class="info-value">${r.doctor}</span></div>
      <div class="info-item"><span class="info-label">Type</span><span class="info-value">${r.reportType.toUpperCase()}</span></div>
      <div class="info-item"><span class="info-label">Upload Date</span><span class="info-value">${new Date(r.uploadDate).toLocaleString()}</span></div>
      <div class="info-item"><span class="info-label">Imaging Ref</span><span class="info-value">${r.imaging_id || 'None'}</span></div>
    </div>`;

  // Imaging study
  if (img) {
    document.getElementById('imaging-card').style.display = 'block';
    const analysis = img.ai_analysis;
    document.getElementById('imaging-details').innerHTML = `
      <div class="info-grid">
        <div class="info-item"><span class="info-label">Study</span><span class="info-value">${img.type}</span></div>
        <div class="info-item"><span class="info-label">Status</span><span class="info-value"><span class="badge ${badgeClass(img.status)}">${img.status}</span></span></div>
        <div class="info-item"><span class="info-label">Uploaded</span><span class="info-value">${new Date(img.uploaded_at).toLocaleString()}</span></div>
        <div class="info-item"><span class="info-label">Doctor</span><span class="info-value">${img.doctor_id}</span></div>
      </div>
      ${analysis ? `
        <div class="ai-card mt-2">
          <h4 style="color:var(--accent-cyan);margin-bottom:8px">🧠 AI Analysis</h4>
          <p style="color:var(--text-secondary)">${analysis.patient_alert || analysis.patient_summary || 'Analysis complete.'}</p>
        </div>` : ''}`;
  }
}

// ── Download ────────────────────────────────────────────────
async function downloadReport() {
  if (!reportData) return;
  const btn = document.getElementById('btn-download');
  btn.textContent = '⏳ Generating...';
  btn.disabled = true;
  try {
    const res = await fetch(`${API}/api/patient/reports/${reportData.report.id}/download`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${reportData.report.reportName.replace(/\s+/g, '_')}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch(e) { console.error(e); }
  finally { btn.textContent = '⬇ Download PDF'; btn.disabled = false; }
}

// ── Translation ─────────────────────────────────────────────
function openTranslateModal() {
  document.getElementById('translation-card').style.display = 'block';
  document.getElementById('translation-card').scrollIntoView({ behavior: 'smooth' });
}

async function runTranslation() {
  if (!reportData) return;
  const lang = document.getElementById('viewer-translate-lang').value;
  const resultDiv = document.getElementById('viewer-translate-result');
  resultDiv.innerHTML = '<div style="text-align:center"><div class="spinner"></div><p style="margin-top:8px">Translating...</p></div>';

  try {
    const res = await fetch(`${API}/api/reports/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        report_id: reportData.report.id, 
        target_language: lang,
        text: reportData.report.summary || reportData.report.reportName
      }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    // FIX 5 - Replace dynamically
    if (data.translated) {
      reportData.report.summary = data.translated;
      renderReport();
    }

    resultDiv.innerHTML = `
      <div class="translate-box"><div class="translate-label">Original</div><p>${data.original}</p></div>
      <div class="translate-box"><div class="translate-label">Simplified (Patient-Friendly)</div><p>${data.simplified}</p></div>
      ${data.translated !== data.simplified ? `<div class="translate-box"><div class="translate-label">Translated (${data.language})</div><p>${data.translated}</p></div>` : ''}
      <div style="margin-top:12px">
        <button class="btn btn-ghost btn-sm" onclick="speakViewerTranslation()">🔊 Listen to Translation</button>
      </div>`;
  } catch(e) {
    resultDiv.innerHTML = '<p style="color:var(--accent-rose)">Translation failed. Please retry.</p>';
  }
}

function speakViewerTranslation() {
  const els = document.querySelectorAll('#viewer-translate-result .translate-box p');
  const text = els.length ? els[els.length - 1].textContent : '';
  if (text) listenReport(text);
}

// ── TTS ─────────────────────────────────────────────────────
function listenReport(textOverride) {
  if (!('speechSynthesis' in window)) { alert('TTS not supported'); return; }
  speechSynthesis.cancel();
  const text = textOverride || (reportData ? `${reportData.report.reportName}. ${reportData.report.summary}` : '');
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.9;
  u.onend = () => { document.getElementById('tts-player').style.display = 'none'; };
  speechSynthesis.speak(u);
  document.getElementById('tts-player').style.display = 'block';
}

function stopTTS() {
  speechSynthesis.cancel();
  document.getElementById('tts-player').style.display = 'none';
}

// ── Share ───────────────────────────────────────────────────
async function shareReport() {
  const url = window.location.href;
  if (navigator.share) {
    try { await navigator.share({ title: reportData?.report.reportName || 'Report', url }); }
    catch(e) { /* cancelled */ }
  } else {
    await navigator.clipboard.writeText(url);
    const btn = document.getElementById('btn-share');
    btn.textContent = '✅ Link Copied!';
    setTimeout(() => btn.textContent = '📤 Share', 2000);
  }
}

init();
