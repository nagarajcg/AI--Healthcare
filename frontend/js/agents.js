// AI Agents Monitor logic

async function init() {
  await loadPending();
  await loadLogs();
}

async function loadPending() {
  const { imaging_records } = await get('/api/agents/imaging');
  const { patients } = await get('/api/patients/');
  const ptMap = {}; patients.forEach(p => ptMap[p.id] = p.name);
  const pending = imaging_records.filter(i => i.status === 'pending');
  const sel = document.getElementById('pending-select');
  sel.innerHTML = pending.length
    ? pending.map(i => `<option value="${i.id}">${i.id} — ${ptMap[i.patient_id]||i.patient_id} — ${i.type}</option>`).join('')
    : '<option value="">No pending images</option>';
}

async function runPipeline() {
  const imgId = document.getElementById('pending-select').value;
  if (!imgId) return alert('No pending image selected');

  const btn = document.getElementById('analyze-btn');
  btn.disabled = true;
  btn.textContent = '⏳ Running…';

  // Animate pipeline steps
  const steps = ['step-screener', 'step-specialist', 'step-translator', 'step-regulatory'];
  for (let i = 0; i < steps.length; i++) {
    document.getElementById(steps[i]).classList.add('active');
    await sleep(600);
    document.getElementById(steps[i]).classList.remove('active');
    document.getElementById(steps[i]).classList.add('done');
  }

  const res = await post('/api/agents/analyze', { imaging_id: imgId });
  btn.disabled = false;
  btn.textContent = '🚀 Run Full Pipeline';

  if (res.analysis && !res.analysis.error) {
    const a = res.analysis;
    const s = a.imaging || {};
    const sp = a.doctor_report || {};
    const comp = a.hospital_storage || {};
    document.getElementById('pipeline-result').innerHTML = `
      <div class="analysis-panel">
        <h3 class="mb-2">✅ Analysis Complete — ${a.imaging_id}</h3>
        <div class="grid-2" style="gap:16px">
          <div class="analysis-section">
            <h4>🔍 Imaging Agent</h4>
            <p>${s.finding}</p>
            <p class="mt-1"><span class="badge ${badgeClass(s.severity)}">${s.severity}</span> · Confidence: ${((s.confidence||0)*100).toFixed(0)}%</p>
            <div class="confidence-bar"><div class="fill" style="width:${(s.confidence||0)*100}%"></div></div>
          </div>
          <div class="analysis-section">
            <h4>👨‍⚕️ Doctor Agent</h4>
            <p>${sp.clinical_report}</p>
            <p class="mt-1"><span class="badge badge-blue">${sp.recommendation}</span></p>
          </div>
          <div class="analysis-section">
            <h4>📱 Patient Agent</h4>
            <p>${a.patient_alert}</p>
          </div>
          <div class="analysis-section">
            <h4>🏥 Hospital Agent</h4>
            <p>${comp.stored ? '✅ Data stored and checks passed' : '❌ Issues found'}</p>
            <ul style="padding-left:18px;margin-top:6px;color:var(--text-secondary);font-size:.85rem">${(comp.notes||[]).map(n=>`<li>${n}</li>`).join('')}</ul>
          </div>
        </div>
      </div>`;
  } else {
    document.getElementById('pipeline-result').innerHTML = `<p style="color:var(--accent-rose)">Error: ${res.analysis?.error || 'Unknown error'}</p>`;
  }

  await loadPending();
  await loadLogs();

  // Reset pipeline viz after a moment
  setTimeout(() => {
    steps.forEach(s => {
      document.getElementById(s).classList.remove('done');
    });
  }, 3000);
}

async function loadLogs() {
  const { logs } = await get('/api/agents/logs');
  document.getElementById('agent-logs').innerHTML = logs.length
    ? `<div class="timeline">${logs.slice().reverse().map(l => `
        <div class="timeline-item">
          <div class="tl-agent">${l.agent}</div>
          <div class="tl-message">${l.message}</div>
          <div class="tl-time">${l.imaging_id} · ${timeAgo(l.timestamp)}</div>
        </div>`).join('')}</div>`
    : '<div class="empty-state"><div class="icon">📜</div><p>No agent activity yet. Run an analysis above to see logs.</p></div>';
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

init();
