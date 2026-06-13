const API = 'http://localhost:8000';

async function handleResponse(res) {
  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return res.json();
  }
  const text = await res.text();
  if (!res.ok) {
    return { success: false, error: text || res.statusText };
  }
  return { success: true, message: text };
}

async function get(path) {
  const res = await fetch(`${API}${path}`);
  return handleResponse(res);
}

async function post(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return handleResponse(res);
}

async function patch(path) {
  const res = await fetch(`${API}${path}`, { method: 'PATCH' });
  return handleResponse(res);
}

async function put(path, body = {}) {
  const res = await fetch(`${API}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return handleResponse(res);
}

async function del(path) {
  const res = await fetch(`${API}${path}`, { method: 'DELETE' });
  return handleResponse(res);
}

function badgeClass(status) {
  const map = {
    pending: 'badge-amber', analyzed: 'badge-cyan', approved: 'badge-green',
    rejected: 'badge-rose', active: 'badge-green', completed: 'badge-blue',
    in_progress: 'badge-purple', online: 'badge-green', offline: 'badge-rose',
    normal: 'badge-green', low: 'badge-blue', moderate: 'badge-amber', high: 'badge-rose',
  };
  return map[status] || 'badge-blue';
}

function severityDotClass(s) {
  const map = { normal: 'normal', low: 'normal', moderate: 'moderate', high: 'high' };
  return map[s] || 'normal';
}

function timeAgo(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Global Modal Scroll Lock ────────────────────────────────
// Automatically locks body scroll when any modal-backdrop is open
// and unlocks when all modals close. Works across all pages.
(function() {
  function updateBodyScroll() {
    const anyOpen = document.querySelector('.modal-backdrop.open');
    if (anyOpen) {
      document.body.classList.add('modal-open');
    } else {
      document.body.classList.remove('modal-open');
    }
  }

  // Watch for class changes on all modal backdrops
  const observer = new MutationObserver(updateBodyScroll);

  // Observe once DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      document.querySelectorAll('.modal-backdrop').forEach(el => {
        observer.observe(el, { attributes: true, attributeFilter: ['class'] });
      });
    });
  } else {
    document.querySelectorAll('.modal-backdrop').forEach(el => {
      observer.observe(el, { attributes: true, attributeFilter: ['class'] });
    });
  }

  // Also observe body for dynamically added modals
  const bodyObserver = new MutationObserver(() => {
    document.querySelectorAll('.modal-backdrop').forEach(el => {
      observer.observe(el, { attributes: true, attributeFilter: ['class'] });
    });
  });
  if (document.body) {
    bodyObserver.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      bodyObserver.observe(document.body, { childList: true, subtree: true });
    });
  }

  // Close modal on backdrop click (clicking outside the modal box)
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop') && e.target.classList.contains('open')) {
      e.target.classList.remove('open');
      updateBodyScroll();
    }
  });

  // Close modal on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const openModal = document.querySelector('.modal-backdrop.open');
      if (openModal) {
        openModal.classList.remove('open');
        updateBodyScroll();
      }
    }
  });
})();

