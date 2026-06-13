// Doctor Dashboard Logic — with DICOM Upload, Metadata, Preview
let currentDoctor = null;
let selectedDicomFile = null;

// ── Init ────────────────────────────────────────────────────
async function init() {
  const { doctors } = await get('/api/doctors/');
  const sel = document.getElementById('doctor-select');
  sel.innerHTML = doctors.map(d =>
    `<option value="${d.id}">${d.name} — ${d.specialty} (${d.status})</option>`
  ).join('');
  if (doctors.length) { sel.value = doctors[0].id; loadDoctor(); }
  setupDicomDropZone();
}

// ── Load Doctor ─────────────────────────────────────────────
async function loadDoctor() {
  const id = document.getElementById('doctor-select').value;
  if (!id) return;
  const { doctor, assigned_images } = await get(`/api/doctors/${id}`);
  const { patients } = await get(`/api/doctors/${id}/patients`);
  const dicomData = await get(`/api/doctor/my-scans/${id}`);
  currentDoctor = doctor;

  // Stats
  const analyzed = assigned_images.filter(i => i.status === 'analyzed').length;
  const pending = assigned_images.filter(i => i.status === 'pending').length;
  const approved = assigned_images.filter(i => i.status === 'approved').length;
  const dicomCount = dicomData.scans ? dicomData.scans.length : 0;
  document.getElementById('stats-row').innerHTML = `
    <div class="stat-card blue"><div class="stat-icon">👥</div><div class="stat-value">${patients.length}</div><div class="stat-label">Patients</div></div>
    <div class="stat-card purple"><div class="stat-icon">🖼️</div><div class="stat-value">${assigned_images.length}</div><div class="stat-label">Imaging Records</div></div>
    <div class="stat-card green"><div class="stat-icon">🔬</div><div class="stat-value">${dicomCount}</div><div class="stat-label">DICOM Scans</div></div>
    <div class="stat-card amber"><div class="stat-icon">✅</div><div class="stat-value">${analyzed + approved}</div><div class="stat-label">Analyzed</div></div>
  `;

  // Patient table
  document.getElementById('patient-table').innerHTML = patients.length
    ? patients.map(p => `<tr>
        <td>${p.id}</td><td>${p.name}</td><td>${p.age}</td>
        <td>${p.condition}</td><td><span class="badge ${badgeClass(p.status)}">${p.status}</span></td>
        <td><button class="btn btn-primary btn-sm" onclick="openPrescriptionModal('${p.id}', '${p.name.replace(/'/g, "\\'")}')">💊 Prescription</button></td>
      </tr>`).join('')
    : '<tr><td colspan="6" class="text-center" style="color:var(--text-muted)">No patients assigned</td></tr>';

  // Imaging table
  const ptMap = {};
  patients.forEach(p => ptMap[p.id] = p.name);
  document.getElementById('imaging-table').innerHTML = assigned_images.length
    ? assigned_images.map(i => `<tr>
        <td>${i.id}</td><td>${ptMap[i.patient_id] || i.patient_id}</td><td>${i.type}</td>
        <td><span class="badge ${badgeClass(i.status)}">${i.status}</span></td>
        <td>
          ${i.status === 'pending' ? `<button class="btn btn-primary btn-sm" onclick="runAnalysis('${i.id}')">🤖 Run AI</button>` : ''}
          ${i.ai_analysis ? `<button class="btn btn-ghost btn-sm" onclick='showAnalysis(${JSON.stringify(i.ai_analysis).replace(/'/g,"&#39;")})'>📄 View Report</button>` : ''}
          ${i.status === 'analyzed' ? `<button class="btn btn-success btn-sm" onclick="approveImage('${i.id}',true)">✅ Approve</button><button class="btn btn-danger btn-sm" onclick="approveImage('${i.id}',false)" style="margin-left:4px">❌ Reject</button>` : ''}
        </td>
      </tr>`).join('')
    : '<tr><td colspan="5" class="text-center" style="color:var(--text-muted)">No imaging records</td></tr>';

  // DICOM scans table
  renderDicomTable(dicomData.scans || []);

  // Populate upload modals
  const allPats = await get('/api/patients/');
  document.getElementById('upload-patient').innerHTML = allPats.patients.map(p =>
    `<option value="${p.id}">${p.name} (${p.id})</option>`
  ).join('');
  document.getElementById('dicom-patient').innerHTML = allPats.patients.map(p =>
    `<option value="${p.id}">${p.name} (${p.id})</option>`
  ).join('');
}

// ── DICOM Table ─────────────────────────────────────────────
function renderDicomTable(scans) {
  const tbody = document.getElementById('dicom-table');
  if (!scans.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center" style="color:var(--text-muted)">No DICOM scans uploaded yet. Click "Upload DICOM" to get started.</td></tr>';
    return;
  }
  tbody.innerHTML = scans.map(s => {
    const title = s.scan_title || s.title || 'Untitled';
    const date = new Date(s.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    const size = s.file_size_formatted || formatBytes(s.file_size || 0);
    return `<tr>
      <td><span class="badge badge-cyan">${s.study_id || '—'}</span></td>
      <td>${s.patient_name || s.patient_id}</td>
      <td>${title}</td>
      <td>${s.scan_type}</td>
      <td>${s.body_part}</td>
      <td><span style="font-size:.82rem;color:var(--text-muted)">${date}</span><br><span style="font-size:.72rem;color:var(--text-muted)">${size}</span></td>
      <td><span class="badge ${badgeClass(s.status)}">${s.status}</span></td>
      <td>
        <div style="display:flex;gap:4px;flex-wrap:wrap">
          <button class="btn btn-ghost btn-sm" onclick="viewMetadata('${s.id}')" title="View Metadata">📋 Meta</button>
          <button class="btn btn-ghost btn-sm" onclick="viewScan('${s.id}')" title="View Scan">👁 View</button>
          <button class="btn btn-danger btn-sm" onclick="deleteScan('${s.id}')" title="Delete" style="padding:6px 10px">🗑</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// ── Tab Navigation ──────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById(`tab-${name}`).classList.add('active');
  event.target.classList.add('active');
}

// ── DICOM Upload ────────────────────────────────────────────
function openDicomUpload() {
  selectedDicomFile = null;
  document.getElementById('dicom-title').value = '';
  document.getElementById('dicom-notes').value = '';
  document.getElementById('dicom-file').value = '';
  document.getElementById('dicom-upload-status').innerHTML = '';
  document.getElementById('drop-zone-content').innerHTML = `
    <div class="drop-icon">📁</div>
    <p>Click or drag & drop a <strong>.dcm, .jpg, or .png</strong> file here</p>
    <span class="drop-hint">Images will be automatically converted to DICOM format</span>`;
  document.getElementById('dicom-drop-zone').classList.remove('has-file');
  document.getElementById('dicom-upload-modal').classList.add('open');
}

function closeDicomUpload() {
  document.getElementById('dicom-upload-modal').classList.remove('open');
}

function setupDicomDropZone() {
  const zone = document.getElementById('dicom-drop-zone');
  if (!zone) return;

  zone.addEventListener('click', () => document.getElementById('dicom-file').click());

  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) validateAndSetFile(file);
  });
}

function handleDicomFile(input) {
  if (input.files[0]) validateAndSetFile(input.files[0]);
}

function validateAndSetFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  const status = document.getElementById('dicom-upload-status');
  const allowed = ['dcm', 'jpg', 'jpeg', 'png'];

  if (!allowed.includes(ext)) {
    status.innerHTML = `<div class="login-toast error">❌ Invalid file type (.${ext}). Accepted formats: .dcm, .jpg, .png.</div>`;
    selectedDicomFile = null;
    return;
  }

  selectedDicomFile = file;
  status.innerHTML = '';
  const zone = document.getElementById('dicom-drop-zone');
  zone.classList.add('has-file');
  document.getElementById('drop-zone-content').innerHTML = `
    <div class="drop-icon">✅</div>
    <p><strong>${file.name}</strong></p>
    <span class="drop-hint">${formatBytes(file.size)} — DICOM file ready</span>`;
}

async function submitDicomUpload() {
  const doctorId = document.getElementById('doctor-select').value;
  const patientId = document.getElementById('dicom-patient').value;
  const title = document.getElementById('dicom-title').value.trim();
  const scanType = document.getElementById('dicom-scan-type').value;
  const bodyPart = document.getElementById('dicom-body-part').value;
  const notes = document.getElementById('dicom-notes').value.trim();
  const status = document.getElementById('dicom-upload-status');
  const btn = document.getElementById('dicom-submit-btn');

  if (!title) { status.innerHTML = '<div class="login-toast error">❌ Please enter a scan title.</div>'; return; }
  if (!selectedDicomFile) { status.innerHTML = '<div class="login-toast error">❌ Please select a DICOM (.dcm) file.</div>'; return; }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-small"></span> Processing...';
  status.innerHTML = '<div class="login-toast" style="background:rgba(6,182,212,.1);color:var(--accent-cyan);border:1px solid rgba(6,182,212,.2)">⏳ Uploading and processing file...</div>';

  const formData = new FormData();
  formData.append('file', selectedDicomFile);
  formData.append('patient_id', patientId);
  formData.append('doctor_id', doctorId);
  formData.append('scan_title', title);
  formData.append('scan_type', scanType);
  formData.append('body_part', bodyPart);
  formData.append('notes', notes);

  try {
    const res = await fetch(`${API}/api/doctor/upload-dicom`, { method: 'POST', body: formData });
    const data = await res.json();
    if (data.success) {
      status.innerHTML = '<div class="login-toast success">✅ DICOM scan uploaded successfully! Metadata extracted.</div>';
      setTimeout(() => { closeDicomUpload(); loadDoctor(); }, 1200);
    } else {
      status.innerHTML = `<div class="login-toast error">❌ ${data.detail || 'Upload failed'}</div>`;
    }
  } catch (e) {
    status.innerHTML = `<div class="login-toast error">❌ Upload error: ${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '📤 Upload DICOM Scan';
  }
}

// ── View Metadata ───────────────────────────────────────────
async function viewMetadata(scanId) {
  const res = await get(`/api/doctor/scan-metadata/${scanId}`);
  if (!res.scan) return;

  const s = res.scan;
  const m = res.metadata || {};
  const title = s.scan_title || s.title || 'Untitled';

  document.getElementById('metadata-content').innerHTML = `
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
            <div class="info-item"><span class="info-label">File Size</span><span class="info-value">${s.file_size_formatted || formatBytes(s.file_size || 0)}</span></div>
            <div class="info-item"><span class="info-label">File Name</span><span class="info-value">${s.file_name || '—'}</span></div>
            <div class="info-item"><span class="info-label">Upload Date</span><span class="info-value">${new Date(s.created_at).toLocaleString()}</span></div>
          </div>
        </div>
        <div class="metadata-section">
          <h4 style="color:var(--accent-purple);font-size:.85rem;margin-bottom:10px">🏥 DICOM Metadata</h4>
          <div class="info-grid">
            <div class="info-item"><span class="info-label">Patient Name</span><span class="info-value">${m.patient_name || '—'}</span></div>
            <div class="info-item"><span class="info-label">Patient ID</span><span class="info-value">${m.patient_id || '—'}</span></div>
            <div class="info-item"><span class="info-label">Study Date</span><span class="info-value">${m.study_date || '—'}</span></div>
            <div class="info-item"><span class="info-label">Modality</span><span class="info-value">${m.modality || '—'}</span></div>
            <div class="info-item"><span class="info-label">Body Part</span><span class="info-value">${m.body_part || '—'}</span></div>
            <div class="info-item"><span class="info-label">Dimensions</span><span class="info-value">${m.image_dimensions || '—'}</span></div>
          </div>
        </div>
      </div>
      <div class="mt-2 metadata-section">
        <h4 style="color:var(--accent-green);font-size:.85rem;margin-bottom:10px">🔧 Technical Details</h4>
        <div class="info-grid" style="grid-template-columns:1fr 1fr 1fr">
          <div class="info-item"><span class="info-label">Institution</span><span class="info-value">${m.institution || '—'}</span></div>
          <div class="info-item"><span class="info-label">Manufacturer</span><span class="info-value">${m.manufacturer || '—'}</span></div>
          <div class="info-item"><span class="info-label">Study Desc.</span><span class="info-value">${m.study_description || '—'}</span></div>
          <div class="info-item"><span class="info-label">Bits Allocated</span><span class="info-value">${m.bits_allocated || '—'}</span></div>
          <div class="info-item"><span class="info-label">Bits Stored</span><span class="info-value">${m.bits_stored || '—'}</span></div>
          <div class="info-item"><span class="info-label">Photometric</span><span class="info-value">${m.photometric_interpretation || '—'}</span></div>
        </div>
      </div>
      ${s.notes ? `<div class="mt-2"><h4 style="color:var(--accent-amber);font-size:.85rem;margin-bottom:6px">📝 Clinical Notes</h4><p style="color:var(--text-secondary);font-size:.9rem">${s.notes}</p></div>` : ''}
    </div>`;
  document.getElementById('metadata-modal').classList.add('open');
}

function closeMetadataModal() {
  document.getElementById('metadata-modal').classList.remove('open');
}

// ── View Scan (DICOM Preview) ───────────────────────────────
function viewScan(scanId) {
  document.getElementById('viewer-content').innerHTML = `
    <div style="text-align:center;width:100%">
      <div class="spinner" style="margin:40px auto"></div>
      <p style="color:var(--text-muted);font-size:.85rem">Loading DICOM preview...</p>
    </div>`;
  document.getElementById('viewer-modal').classList.add('open');

  const img = new Image();
  img.onload = () => {
    document.getElementById('viewer-content').innerHTML = `
      <div style="text-align:center;width:100%">
        <img src="${API}/api/scan-preview/${scanId}" alt="DICOM Preview" style="max-width:100%;max-height:500px;border-radius:var(--radius-md);border:1px solid var(--border-subtle)">
        <p style="color:var(--text-muted);font-size:.78rem;margin-top:12px">DICOM Preview — Window-leveled render</p>
      </div>`;
  };
  img.onerror = () => {
    document.getElementById('viewer-content').innerHTML = `
      <div style="text-align:center;padding:60px 20px">
        <div style="font-size:3rem;margin-bottom:16px;opacity:.5">🔬</div>
        <h4 style="color:var(--text-primary);margin-bottom:8px">DICOM Preview Unavailable</h4>
        <p style="color:var(--text-muted);font-size:.85rem">The DICOM preview could not be generated. The original .dcm file is intact and can be downloaded.</p>
      </div>`;
  };
  img.src = `${API}/api/scan-preview/${scanId}`;
}

function closeViewerModal() {
  document.getElementById('viewer-modal').classList.remove('open');
}

// ── Delete Scan ─────────────────────────────────────────────
async function deleteScan(scanId) {
  if (!confirm('Are you sure you want to delete this DICOM scan? This action cannot be undone.')) return;
  try {
    const res = await fetch(`${API}/api/doctor/scan/${scanId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) { loadDoctor(); }
    else { alert(data.detail || 'Delete failed'); }
  } catch (e) {
    alert('Error deleting scan: ' + e.message);
  }
}

// ── Existing Functions ──────────────────────────────────────
async function runAnalysis(imgId) {
  const res = await post('/api/agents/analyze', { imaging_id: imgId });
  if (res.analysis) { showAnalysis(res.analysis); loadDoctor(); }
}

function showAnalysis(a) {
  const s = a.imaging || {};
  const sp = a.doctor_report || {};
  const comp = a.hospital_storage || {};
  document.getElementById('analysis-result').innerHTML = `
    <div class="analysis-panel">
      <h3 class="mb-2">📊 AI Analysis Report — ${a.imaging_id}</h3>
      <div class="analysis-section">
        <h4>🔍 Imaging Agent</h4>
        <p><strong>Finding:</strong> ${s.finding || 'N/A'}</p>
        <p><strong>Severity:</strong> <span class="badge ${badgeClass(s.severity)}">${s.severity || 'N/A'}</span></p>
        <p style="margin-top:6px"><strong>Confidence:</strong> ${((s.confidence||0)*100).toFixed(0)}%</p>
        <div class="confidence-bar"><div class="fill" style="width:${(s.confidence||0)*100}%"></div></div>
      </div>
      <div class="analysis-section">
        <h4>👨‍⚕️ Doctor Agent</h4>
        <p>${sp.clinical_report || 'N/A'}</p>
        <p class="mt-1"><strong>Recommendation:</strong> ${sp.recommendation || 'N/A'}</p>
      </div>
      <div class="analysis-section">
        <h4>📱 Patient Agent</h4>
        <p>${a.patient_alert || 'N/A'}</p>
      </div>
      <div class="analysis-section">
        <h4>🏥 Hospital Agent</h4>
        <p>${comp.stored ? '✅ Data stored and checks passed' : '❌ Issues found'}</p>
        <ul style="margin-top:6px;padding-left:18px;color:var(--text-secondary);font-size:.875rem">${(comp.notes||[]).map(n => `<li>${n}</li>`).join('')}</ul>
      </div>
    </div>`;
}

async function approveImage(imgId, approved) {
  const notes = approved ? '' : prompt('Enter reason for rejection:', '') || '';
  await post('/api/doctors/approve', { imaging_id: imgId, approved, doctor_notes: notes });
  loadDoctor();
}

function openUploadModal() { document.getElementById('upload-modal').classList.add('open'); }
function closeUploadModal() { document.getElementById('upload-modal').classList.remove('open'); }

async function submitUpload() {
  const patientId = document.getElementById('upload-patient').value;
  const type = document.getElementById('upload-type').value;
  const doctorId = document.getElementById('doctor-select').value;
  const response = await post('/api/agents/imaging', { patient_id: patientId, type, doctor_id: doctorId });
  if (response.result) {
    alert(`AI Analysis Complete!\n\nResult: ${response.result}\nRisk Level: ${response.risk}\n\nPatient Explanation:\n${response.explanation}`);
  }
  closeUploadModal();
  loadDoctor();
}

// ── Prescription Workflow ───────────────────────────────────
function openPrescriptionModal(patientId, patientName) {
  document.getElementById('presc-patient-id').value = patientId;
  document.getElementById('presc-patient-name').value = `${patientName} (${patientId})`;
  document.getElementById('presc-diagnosis').value = '';
  document.getElementById('presc-medicines').value = '';
  document.getElementById('presc-dosage').value = '';
  document.getElementById('presc-instructions').value = '';
  document.getElementById('presc-tests').value = '';
  document.getElementById('presc-followup').value = '';
  document.getElementById('presc-upload-status').innerHTML = '';
  document.getElementById('create-prescription-modal').classList.add('open');
}

function closePrescriptionModal() {
  document.getElementById('create-prescription-modal').classList.remove('open');
}

async function submitPrescription() {
  const btn = document.getElementById('presc-submit-btn');
  const status = document.getElementById('presc-upload-status');
  
  const payload = {
    doctor_id: document.getElementById('doctor-select').value,
    patient_id: document.getElementById('presc-patient-id').value,
    diagnosis: document.getElementById('presc-diagnosis').value.trim(),
    medicines: document.getElementById('presc-medicines').value.trim(),
    dosage: document.getElementById('presc-dosage').value.trim(),
    instructions: document.getElementById('presc-instructions').value.trim(),
    test_recommendations: document.getElementById('presc-tests').value.trim(),
    follow_up_date: document.getElementById('presc-followup').value
  };

  if (!payload.diagnosis || !payload.medicines) {
    status.innerHTML = '<div class="login-toast error">❌ Diagnosis and Medicines are required.</div>';
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-small"></span> Sending...';
  status.innerHTML = '';

  try {
    const res = await post('/api/doctor/prescriptions/create', payload);
    if (res.success) {
      status.innerHTML = '<div class="login-toast success">✅ Prescription sent to Staff and Patient!</div>';
      setTimeout(() => {
        closePrescriptionModal();
      }, 1500);
    } else {
      status.innerHTML = `<div class="login-toast error">❌ ${res.detail || 'Failed to create prescription'}</div>`;
    }
  } catch (e) {
    status.innerHTML = `<div class="login-toast error">❌ Error: ${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '📤 Send to Staff & Patient';
  }
}

init();
