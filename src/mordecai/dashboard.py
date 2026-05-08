from __future__ import annotations


def render_dashboard() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mordecai Console</title>
  <style>
    :root {
      --bg: #111215;
      --panel: #1c1f26;
      --panel-2: #252935;
      --text: #f3eee3;
      --muted: #b7ad96;
      --accent: #c59a49;
      --accent-2: #7d3f32;
      --border: rgba(197, 154, 73, 0.24);
      --good: #6fcf97;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--text);
      background:
        radial-gradient(circle at top, rgba(197, 154, 73, 0.15), transparent 32%),
        linear-gradient(180deg, #0d0f13 0%, #151922 100%);
      min-height: 100vh;
    }
    .shell {
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }
    .hero {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
      margin-bottom: 20px;
    }
    .card {
      background: linear-gradient(180deg, rgba(28,31,38,0.95), rgba(18,20,26,0.95));
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 18px 50px rgba(0,0,0,0.35);
    }
    h1, h2 { margin: 0 0 12px; font-weight: 600; }
    h1 { font-size: clamp(2rem, 5vw, 3.6rem); letter-spacing: 0.03em; }
    h2 { font-size: 1.15rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.12em; }
    p { color: var(--muted); line-height: 1.6; }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
      margin-top: 20px;
    }
    .metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
    .metric {
      background: var(--panel-2);
      border-radius: 14px;
      padding: 14px;
      border: 1px solid rgba(255,255,255,0.06);
    }
    .label { font-size: 0.78rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
    .value { margin-top: 6px; font-size: 1.35rem; }
    .terminal {
      width: 100%;
      min-height: 160px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.08);
      background: #0d1117;
      color: #e8dfca;
      padding: 14px;
      margin-bottom: 12px;
      resize: vertical;
    }
    button {
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      background: linear-gradient(135deg, var(--accent), #f1d59d);
      color: #171717;
      font-weight: 700;
      cursor: pointer;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      background: rgba(0,0,0,0.22);
      border-radius: 14px;
      padding: 14px;
      min-height: 120px;
      border: 1px solid rgba(255,255,255,0.06);
    }
    .trace-list {
      display: grid;
      gap: 10px;
    }
    .trace-item {
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px;
      padding: 12px;
      background: rgba(255,255,255,0.03);
    }
    .trace-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-size: 0.9rem;
      color: var(--text);
      margin-bottom: 8px;
    }
    .trace-meta {
      color: var(--muted);
      font-size: 0.82rem;
    }
    .cap-grid {
      display: grid;
      gap: 12px;
    }
    .cap-card {
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px;
      padding: 12px;
      background: rgba(255,255,255,0.03);
    }
    .tag {
      display: inline-flex;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(197, 154, 73, 0.12);
      color: var(--accent);
      margin-right: 8px;
      margin-bottom: 8px;
      font-size: 0.82rem;
    }
    @media (max-width: 800px) {
      .hero, .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="card">
        <h2>Mordecai</h2>
        <h1>The Formal AI Runtime</h1>
        <p>Policy-bound, reversible, git-backed, and built to run as the core AI service for a repurposed Android device.</p>
        <div id="wake-words"></div>
      </div>
      <div class="card metrics" id="metrics"></div>
    </section>
    <section class="grid">
      <div class="card">
        <h2>Dialogue</h2>
        <textarea id="message" class="terminal" placeholder="Speak, Jarin."></textarea>
        <button id="send">Send To Mordecai</button>
        <pre id="reply"></pre>
      </div>
      <div class="card">
        <h2>Policy</h2>
        <pre id="policy"></pre>
      </div>
      <div class="card">
        <h2>Git State</h2>
        <pre id="git"></pre>
      </div>
      <div class="card">
        <h2>Improvement Candidates</h2>
        <pre id="candidates"></pre>
      </div>
      <div class="card">
        <h2>Recent Events</h2>
        <pre id="events"></pre>
      </div>
      <div class="card">
        <h2>Proxy Activity</h2>
        <pre id="proxy"></pre>
      </div>
      <div class="card">
        <h2>Runtime Trace</h2>
        <div id="trace" class="trace-list"></div>
      </div>
      <div class="card">
        <h2>Capabilities Matrix</h2>
        <div id="capabilities" class="cap-grid"></div>
      </div>
    </section>
  </div>
  <script>
    async function load() {
      const [status, policy, gitState, candidates, events, proxyLogs, trace, capabilities] = await Promise.all([
        fetch('/api/status').then(r => r.json()),
        fetch('/api/policy').then(r => r.json()),
        fetch('/api/git/status').then(r => r.json()),
        fetch('/api/improvement/candidates').then(r => r.json()),
        fetch('/api/events').then(r => r.json()),
        fetch('/api/proxy/logs').then(r => r.json()),
        fetch('/api/runtime/trace').then(r => r.json()),
        fetch('/api/runtime/capabilities').then(r => r.json()),
      ]);

      document.getElementById('metrics').innerHTML = `
        <div class="metric"><div class="label">Provider</div><div class="value">${status.provider}</div></div>
        <div class="metric"><div class="label">CPU</div><div class="value">${status.cpu_percent.toFixed(1)}%</div></div>
        <div class="metric"><div class="label">Memory</div><div class="value">${status.memory_mb.toFixed(1)} MB</div></div>
        <div class="metric"><div class="label">Pending</div><div class="value">${status.pending_candidates}</div></div>`;

      document.getElementById('wake-words').innerHTML = status.wake_words.map(word => `<span class="tag">${word}</span>`).join('');
      document.getElementById('policy').textContent = JSON.stringify(policy, null, 2);
      document.getElementById('git').textContent = JSON.stringify(gitState, null, 2);
      document.getElementById('candidates').textContent = JSON.stringify(candidates, null, 2);
      document.getElementById('events').textContent = JSON.stringify(events.slice(-10), null, 2);
      document.getElementById('proxy').textContent = JSON.stringify(proxyLogs.slice(-10), null, 2);
      document.getElementById('trace').innerHTML = trace.events.slice(-8).reverse().map(event => `
        <div class="trace-item">
          <div class="trace-head"><strong>${event.name}</strong><span>${new Date(event.created_at).toLocaleTimeString()}</span></div>
          <div class="trace-meta">${JSON.stringify(event.payload)}</div>
        </div>
      `).join('') || '<div class="trace-item">No trace events yet.</div>';

      const providerCards = Object.entries(capabilities.providers).map(([name, value]) => `
        <div class="cap-card">
          <strong>${name}</strong>
          <pre>${JSON.stringify(value, null, 2)}</pre>
        </div>
      `).join('');
      const toolCards = capabilities.tools.map(tool => `
        <div class="cap-card">
          <strong>${tool.tool}</strong>
          <div class="trace-meta">risk=${tool.risk_level} | confirm=${tool.confirmation_policy} | sandbox=${tool.sandbox_profile}</div>
          <pre>${JSON.stringify(tool, null, 2)}</pre>
        </div>
      `).join('');
      document.getElementById('capabilities').innerHTML = providerCards + toolCards;
    }

    document.getElementById('send').addEventListener('click', async () => {
      const message = document.getElementById('message').value;
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      }).then(r => r.json());
      document.getElementById('reply').textContent = JSON.stringify(response, null, 2);
      await load();
    });

    load();
  </script>
</body>
</html>
"""