// Patient Login Logic

function fillDemo(pid) {
  document.getElementById('patient-id').value = pid;
}

function togglePassword() {
  // Deprecated
}

function showError(msg) {
  const el = document.getElementById('login-error');
  el.textContent = msg;
  el.style.display = 'block';
  document.getElementById('login-success').style.display = 'none';
  setTimeout(() => el.style.display = 'none', 4000);
}

function showSuccess(msg) {
  const el = document.getElementById('login-success');
  el.textContent = msg;
  el.style.display = 'block';
  document.getElementById('login-error').style.display = 'none';
}

async function handleLogin(e) {
  e.preventDefault();
  const patientId = document.getElementById('patient-id').value.trim();
  const remember = document.getElementById('remember-me').checked;

  if (!patientId) { showError('Please enter Patient ID'); return; }

  const btn = document.getElementById('login-btn');
  btn.querySelector('.btn-text').style.display = 'none';
  btn.querySelector('.btn-loader').style.display = 'inline-flex';
  btn.disabled = true;

  try {
    const res = await fetch(`${API}/api/patient/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patientId }),
    });
    const data = await res.json();

    if (!res.ok || !data.success) {
      showError(data.detail || 'Login failed. Please check your credentials.');
      return;
    }

    // Store token
    const storage = remember ? localStorage : sessionStorage;
    storage.setItem('healthai_token', data.token);
    storage.setItem('healthai_patient', JSON.stringify(data.patient));
    localStorage.setItem('healthai_token', data.token);
    localStorage.setItem('healthai_patient', JSON.stringify(data.patient));

    showSuccess(`Welcome back, ${data.patient.name}! Redirecting...`);
    setTimeout(() => window.location.href = '/pages/patient.html', 800);
  } catch (err) {
    showError('Network error. Please try again.');
  } finally {
    btn.querySelector('.btn-text').style.display = 'inline-flex';
    btn.querySelector('.btn-loader').style.display = 'none';
    btn.disabled = false;
  }
}

function showForgotPassword(e) {
  e.preventDefault();
  document.getElementById('forgot-modal').classList.add('open');
}

function closeForgotModal() {
  document.getElementById('forgot-modal').classList.remove('open');
}

function sendResetOTP() {
  const pid = document.getElementById('forgot-pid').value.trim();
  if (!pid) return;
  const msg = document.getElementById('forgot-msg');
  msg.textContent = `OTP sent to the phone number registered with ${pid}. Please check your messages.`;
  msg.style.display = 'block';
}

// If already logged in, redirect
(function checkAuth() {
  const token = localStorage.getItem('healthai_token');
  if (token) {
    window.location.href = '/pages/patient.html';
  }
})();
