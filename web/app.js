const state = { jobs: [], sort: { key: 'posted_date', asc: false }, page: 1, pageSize: 12 };
const $ = (id) => document.getElementById(id);

function escapeHtml(value) { const element = document.createElement('div'); element.textContent = value; return element.innerHTML; }
function formatDate(value) { if (!value) return '—'; const date = new Date(`${value.slice(0, 10)}T00:00:00`); return Number.isNaN(date) ? value : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }); }
function formatTimestamp(value) { const date = new Date(value); return Number.isNaN(date) ? '—' : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }); }

function setLoadError(message) {
  $('status').className = 'status error';
  $('status').innerHTML = '<i></i> Data unavailable';
  $('runMessage').textContent = 'The latest tracker data could not be loaded.';
  $('errorMessage').textContent = message;
  $('errorDetails').textContent = 'The static dashboard reads web/jobs.json generated from the committed Excel workbook.';
  $('errorPanel').classList.remove('hidden');
}

function showStats() {
  const countries = new Set(state.jobs.map((job) => job.country).filter(Boolean));
  const latest = state.jobs.map((job) => job.posted_date).filter(Boolean).sort().at(-1);
  $('statsSection').innerHTML = [
    ['Jobs in tracker', state.jobs.length], ['Countries', countries.size],
    ['Latest posting', latest ? formatDate(latest) : '—'], ['Data source', 'GitHub Actions'],
  ].map(([label, value]) => `<article class="stat"><div class="label">${label}</div><div class="number">${escapeHtml(String(value))}</div></article>`).join('');
  $('statsSection').classList.remove('hidden');
}

function filteredJobs() {
  const query = $('search').value.trim().toLowerCase();
  const country = $('country').value;
  return state.jobs.filter((job) => (!query || `${job.title} ${job.country}`.toLowerCase().includes(query)) && (!country || job.country === country)).sort((left, right) => {
    const a = (left[state.sort.key] || '').toLowerCase(); const b = (right[state.sort.key] || '').toLowerCase();
    return (a > b ? 1 : a < b ? -1 : 0) * (state.sort.asc ? 1 : -1);
  });
}

function renderTable() {
  const jobs = filteredJobs(); const pages = Math.max(1, Math.ceil(jobs.length / state.pageSize));
  state.page = Math.min(state.page, pages);
  const rows = jobs.slice((state.page - 1) * state.pageSize, state.page * state.pageSize);
  $('jobCount').textContent = `${jobs.length} ${jobs.length === 1 ? 'job' : 'jobs'}${jobs.length !== state.jobs.length ? ' matching filters' : ' loaded'}`;
  const hasJobs = state.jobs.length > 0;
  $('emptyState').classList.toggle('hidden', hasJobs); $('tableTools').classList.toggle('hidden', !hasJobs); $('tableWrap').classList.toggle('hidden', !hasJobs); $('pagination').classList.toggle('hidden', !hasJobs);
  $('jobsBody').innerHTML = rows.length ? rows.map((job) => `<tr><td>${escapeHtml(job.country)}</td><td>${formatDate(job.posted_date)}</td><td>${escapeHtml(job.title)}</td><td><a class="job-link" href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer">View on LinkedIn ↗</a></td></tr>`).join('') : '<tr><td colspan="4" class="no-matches">No matching jobs found</td></tr>';
  $('pagination').innerHTML = pages > 1 ? `<button ${state.page === 1 ? 'disabled' : ''} data-page="${state.page - 1}">Previous</button>${Array.from({ length: pages }, (_, index) => `<button class="${index + 1 === state.page ? 'active' : ''}" data-page="${index + 1}">${index + 1}</button>`).join('')}<button ${state.page === pages ? 'disabled' : ''} data-page="${state.page + 1}">Next</button>` : '';
}

async function loadDashboard() {
  try {
    const response = await fetch('jobs.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`Static data request failed (${response.status}).`);
    if (!(response.headers.get('content-type') || '').includes('application/json')) throw new Error('Static tracker data did not return JSON.');
    const payload = await response.json();
    if (!Array.isArray(payload.jobs)) throw new Error('Static tracker data has an invalid jobs list.');
    state.jobs = payload.jobs;
    $('lastRun').textContent = `Last update: ${formatTimestamp(payload.generated_at)}`;
    const countries = [...new Set(state.jobs.map((job) => job.country).filter(Boolean))].sort();
    $('country').innerHTML = '<option value="">All countries</option>' + countries.map((country) => `<option>${escapeHtml(country)}</option>`).join('');
    showStats(); renderTable();
  } catch (error) { setLoadError(error.message); }
}

function initialise() {
  $('search').addEventListener('input', () => { state.page = 1; renderTable(); });
  $('country').addEventListener('change', () => { state.page = 1; renderTable(); });
  document.querySelectorAll('th[data-key]').forEach((header) => header.addEventListener('click', () => { const key = header.dataset.key; state.sort = { key, asc: state.sort.key === key ? !state.sort.asc : true }; renderTable(); }));
  $('pagination').addEventListener('click', (event) => { if (event.target.dataset.page) { state.page = Number(event.target.dataset.page); renderTable(); } });
  loadDashboard();
}

initialise();
