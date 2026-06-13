// Hospital Staff Dashboard logic

async function loadAll() {
  await Promise.all([loadStats(), loadPatientTable(), loadTasks(), loadImaging(), loadAppointments(), loadStaffNotifications()]);
}

// ... existing functions ...

async function loadStaffNotifications() {
  try {
    const { notifications } = await get('/api/staff/notifications');
    const container = document.getElementById('staff-notifications-list');
    const countEl = document.getElementById('staff-notif-count');
    
    if (countEl) countEl.textContent = notifications.length;
    
    if (!notifications.length) {
      container.innerHTML = '<div class="empty-state"><div class="icon">🔔</div><p>No recent updates</p></div>';
      return;
    }
    
    container.innerHTML = notifications.map(n => {
      let icon = '🔔';
      if (n.type === 'appointment_request') icon = '📅';
      if (n.type === 'doctor_update') icon = '🩺';
      if (n.type === 'audit_event') icon = '📋';
      
      return `
        <div class="notification-item">
          <div style="font-size:1.5rem;margin-right:12px">${icon}</div>
          <div style="flex:1">
            <strong style="font-size:.875rem">${n.title}</strong>
            <p style="font-size:.82rem;color:var(--text-secondary);margin-top:2px">${n.message}</p>
            <span style="font-size:.72rem;color:var(--text-muted)">${timeAgo(n.created_at)}</span>
          </div>
          <span class="badge badge-ghost">${n.status || 'info'}</span>
        </div>`;
    }).join('');
  } catch (e) {
    console.error('Error loading staff notifications:', e);
  }
}

async function loadStats() {
  const { stats } = await get('/api/staff/dashboard');
  document.getElementById('stats-grid').innerHTML = `
    <div class="stat-card blue"><div class="stat-icon">👥</div><div class="stat-value">${stats.total_patients}</div><div class="stat-label">Total Patients</div></div>
    <div class="stat-card green"><div class="stat-icon">✅</div><div class="stat-value">${stats.images_analyzed}</div><div class="stat-label">Analyzed</div></div>
    <div class="stat-card amber"><div class="stat-icon">⏳</div><div class="stat-value">${stats.images_pending}</div><div class="stat-label">Pending</div></div>
    <div class="stat-card purple"><div class="stat-icon">🚨</div><div class="stat-value">${stats.images_critical || 0}</div><div class="stat-label">Critical</div></div>
  `;
}

async function loadPatientTable() {
  const { patients } = await get('/api/patients/');
  const { imaging_records } = await get('/api/agents/imaging');
  const { doctors } = await get('/api/doctors/');
  const docMap = {}; doctors.forEach(d => docMap[d.id] = d);
  // Build lookup: patient → imaging record + doctor
  const imgByPatient = {};
  imaging_records.forEach(i => {
    if (!imgByPatient[i.patient_id]) imgByPatient[i.patient_id] = [];
    imgByPatient[i.patient_id].push(i);
  });

  document.getElementById('patient-table').innerHTML = patients.length
    ? patients.map(p => {
      const imgs = imgByPatient[p.id] || [];
      const latestImg = imgs[imgs.length - 1];
      const severity = latestImg?.ai_analysis?.specialist_report?.severity;
      let displayStatus = latestImg ? latestImg.status : p.status;
      // Map to Pending/Critical/Completed
      if (severity === 'high') displayStatus = 'critical';
      else if (displayStatus === 'approved' || p.status === 'completed') displayStatus = 'completed';
      else if (displayStatus === 'analyzed') displayStatus = 'analyzed';
      else displayStatus = 'pending';

      const doc = latestImg ? docMap[latestImg.doctor_id] : null;
      return `<tr>
        <td>${p.id}</td>
        <td><strong>${p.name}</strong></td>
        <td>${p.age}</td>
        <td>${p.condition}</td>
        <td>${doc ? `${doc.name} <span class="badge badge-purple" style="margin-left:4px">${doc.specialty}</span>` : '<span style="color:var(--text-muted)">—</span>'}</td>
        <td>${latestImg ? latestImg.type : '—'}</td>
        <td><span class="status-dot ${displayStatus}"></span> <span class="badge ${badgeClass(displayStatus)}">${displayStatus}</span></td>
      </tr>`;
    }).join('')
    : '<tr><td colspan="7" class="text-center" style="color:var(--text-muted)">No patients registered yet</td></tr>';
}

async function loadTasks() {
  const { tasks } = await get('/api/staff/tasks');
  const priorityIcon = { high: '🔴', medium: '🟡', low: '🟢' };
  document.getElementById('task-list').innerHTML = tasks.length
    ? tasks.map(t => `
      <div class="notification-item" style="align-items:center">
        <span style="font-size:1.2rem">${priorityIcon[t.priority] || '⚪'}</span>
        <div style="flex:1">
          <strong style="font-size:.875rem">${t.title}</strong>
          <p style="font-size:.78rem;color:var(--text-muted)">Assigned: ${t.assigned_to} · ${timeAgo(t.created_at)}</p>
        </div>
        <span class="badge ${badgeClass(t.status)}">${t.status}</span>
        ${t.status !== 'completed' ? `<button class="btn btn-ghost btn-sm" onclick="completeTask('${t.id}')" style="margin-left:8px">✅</button>` : ''}
      </div>`).join('')
    : '<div class="empty-state"><div class="icon">📝</div><p>No tasks</p></div>';
}

async function loadImaging() {
  const { imaging_records } = await get('/api/agents/imaging');
  const { patients } = await get('/api/patients/');
  const ptMap = {}; patients.forEach(p => ptMap[p.id] = p.name);
  document.getElementById('imaging-overview').innerHTML = imaging_records.length
    ? imaging_records.map(i =>
      `<tr><td>${i.id}</td><td>${ptMap[i.patient_id]||i.patient_id}</td><td>${i.type}</td><td><span class="badge ${badgeClass(i.status)}">${i.status}</span></td></tr>`
    ).join('')
    : '<tr><td colspan="4" style="color:var(--text-muted)">No imaging records</td></tr>';
}

async function loadAppointments() {
  const { appointments } = await get('/api/staff/appointments');
  const container = document.getElementById('appointments-list');
  const pending = appointments.filter(a => a.status === 'pending');
  
  if (!pending.length) {
    container.innerHTML = '<div class="empty-state"><div class="icon">✅</div><p>No pending requests</p></div>';
    return;
  }
  
  container.innerHTML = pending.map(a => `
    <div class="notification-item" style="flex-direction:column;align-items:flex-start">
      <div style="display:flex;justify-content:space-between;width:100%">
        <strong>${a.patient_name}</strong>
        <span class="badge badge-amber">Pending</span>
      </div>
      <p style="font-size:.85rem;color:var(--text-secondary)">Doctor: ${a.doctor_name}</p>
      <p style="font-size:.85rem;color:var(--text-secondary)">Date: ${a.appointment_date} (${a.time_slot})</p>
      <p style="font-size:.8rem;color:var(--text-muted);font-style:italic">"${a.reason}"</p>
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn btn-success btn-sm" onclick="approveApt('${a.id}')">Approve</button>
        <button class="btn btn-danger btn-sm" onclick="rejectApt('${a.id}')">Reject</button>
      </div>
    </div>
  `).join('');
}

async function approveApt(id) {
  await put(`/api/staff/appointments/${id}/approve-full`, {});
  loadAll();
}

async function rejectApt(id) {
  await put(`/api/staff/appointments/${id}/reject`, {});
  loadAll();
}

// ── Patient Intake ──────────────────────────────────────────

async function submitIntake() {
  const name = document.getElementById('intake-name').value.trim();
  const age = parseInt(document.getElementById('intake-age').value);
  const gender = document.getElementById('intake-gender').value;
  const contact = document.getElementById('intake-contact').value.trim();
  const problem = document.getElementById('intake-problem').value.trim();
  const scan_type = document.getElementById('intake-scan').value;

  if (!name || !age || !problem) {
    alert('Please fill in Name, Age, and Problem Description.');
    return;
  }

  const btn = document.getElementById('intake-btn');
  btn.disabled = true;
  btn.innerHTML = '⏳ Processing…';

  const res = await post('/api/staff/intake', { name, age, gender, contact, problem, scan_type });

  btn.disabled = false;
  btn.innerHTML = '🚀 Submit & Auto-Assign';

  if (res.success) {
    const doc = res.assigned_doctor;
    const sev = res.analysis?.specialist_report?.severity || 'normal';
    document.getElementById('intake-result').innerHTML = `
      <div class="result-toast">
        <h4>✅ Patient Registered & AI Analysis Complete</h4>
        <div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:12px;font-size:.9rem">
          <div><span style="color:var(--text-muted)">Patient ID</span><br><strong>${res.patient.id}</strong></div>
          <div><span style="color:var(--text-muted)">Assigned Doctor</span><br><strong>${doc.name}</strong> <span class="badge badge-purple">${doc.specialty}</span></div>
          <div><span style="color:var(--text-muted)">AI Severity</span><br><span class="badge ${badgeClass(sev)}">${sev}</span></div>
          <div><span style="color:var(--text-muted)">Scan</span><br><strong>${scan_type}</strong></div>
        </div>
        <p style="margin-top:12px;color:var(--text-secondary);font-size:.85rem">📋 ${res.analysis?.patient_summary || 'Report generated.'}</p>
      </div>`;

    // Clear form
    document.getElementById('intake-name').value = '';
    document.getElementById('intake-age').value = '';
    document.getElementById('intake-contact').value = '';
    document.getElementById('intake-problem').value = '';

    // Refresh data
    await loadAll();
  } else {
    document.getElementById('intake-result').innerHTML = `<p style="color:var(--accent-rose)">Error: ${JSON.stringify(res)}</p>`;
  }
}

// ── Task management ─────────────────────────────────────────

async function completeTask(taskId) {
  await patch(`/api/staff/tasks/${taskId}/status?status=completed`);
  await Promise.all([loadStats(), loadTasks()]);
}

function openTaskModal() { document.getElementById('task-modal').classList.add('open'); }
function closeTaskModal() { document.getElementById('task-modal').classList.remove('open'); }

async function createTask() {
  const title = document.getElementById('task-title').value;
  const assigned_to = document.getElementById('task-assign').value;
  const priority = document.getElementById('task-priority').value;
  if (!title || !assigned_to) return alert('Please fill all fields');
  await post('/api/staff/tasks', { title, assigned_to, priority });
  closeTaskModal();
  await Promise.all([loadStats(), loadTasks()]);
}

// ── Init ────────────────────────────────────────────────────
loadAll();
