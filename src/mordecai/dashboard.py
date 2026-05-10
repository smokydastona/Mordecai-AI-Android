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
    .avatar-stage {
      display: grid;
      gap: 12px;
      align-content: start;
      justify-items: center;
      text-align: center;
    }
    .avatar-frame {
      width: min(100%, 240px);
      aspect-ratio: 1;
      padding: 14px;
      border-radius: 22px;
      border: 1px solid rgba(255,255,255,0.08);
      background: radial-gradient(circle at top, rgba(197,154,73,0.18), rgba(0,0,0,0.05) 50%), var(--panel-2);
    }
    .avatar-frame svg {
      width: 100%;
      height: 100%;
      display: block;
    }
    .avatar-meta {
      color: var(--muted);
      font-size: 0.92rem;
    }
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
    .control-stack {
      display: grid;
      gap: 12px;
    }
    .field {
      display: grid;
      gap: 6px;
    }
    label {
      font-size: 0.82rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    input, select {
      width: 100%;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.08);
      background: #0d1117;
      color: var(--text);
      padding: 12px;
    }
    .row {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
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
        <p>Policy-bound, reversible, git-backed, and built to run as the core AI service for supported Android phones.</p>
        <div id="wake-words"></div>
      </div>
      <div class="card metrics" id="metrics"></div>
      <div class="card avatar-stage">
        <h2>Permanent Avatar</h2>
        <div id="avatar-frame" class="avatar-frame"></div>
        <div id="avatar-meta" class="avatar-meta"></div>
      </div>
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
        <h2>Memory Browser</h2>
        <pre id="memory"></pre>
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
        <h2>Goals</h2>
        <pre id="goals"></pre>
      </div>
      <div class="card">
        <h2>Routines</h2>
        <pre id="routines"></pre>
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
        <h2>Local Models</h2>
        <pre id="local-models"></pre>
      </div>
      <div class="card">
        <h2>Voice Catalog</h2>
        <div class="control-stack">
          <div class="row">
            <div class="field">
              <label for="voice-query">Search</label>
              <input id="voice-query" placeholder="whisper, piper, cloning" />
            </div>
            <div class="field">
              <label for="voice-category">Category</label>
              <select id="voice-category">
                <option value="">All</option>
                <option value="text-to-speech">Text-to-Speech</option>
                <option value="voice-cloning">Voice Cloning</option>
                <option value="speech-recognition">Speech Recognition</option>
                <option value="audio-pipeline">Audio / Voice Pipelines</option>
                <option value="training-framework">Training Frameworks</option>
                <option value="enhancement-restoration">Enhancement / Restoration</option>
                <option value="multimodal-experimental">Multimodal / Experimental</option>
                <option value="master-index">Master Lists</option>
              </select>
            </div>
          </div>
          <div class="row">
            <div class="field">
              <label for="voice-runtime-fit">Runtime Fit</label>
              <select id="voice-runtime-fit">
                <option value="">All</option>
                <option value="phone">Phone</option>
                <option value="server">Server</option>
                <option value="research">Research</option>
              </select>
            </div>
            <div class="field">
              <label for="voice-supported-only">Runtime Supported</label>
              <select id="voice-supported-only">
                <option value="false" selected>All repos</option>
                <option value="true">Only supported</option>
              </select>
            </div>
          </div>
          <button id="apply-voice-filters">Apply Voice Filters</button>
        </div>
        <pre id="voice-catalog"></pre>
      </div>
      <div class="card">
        <h2>Model Provisioning</h2>
        <div class="control-stack">
          <div class="field">
            <label for="model-bundle">Bundle</label>
            <select id="model-bundle"></select>
          </div>
          <div class="field">
            <label for="model-bundle-details">Bundle Details</label>
            <pre id="model-bundle-details"></pre>
          </div>
          <div class="field">
            <label for="model-overwrite">Overwrite Existing Files</label>
            <select id="model-overwrite">
              <option value="false" selected>Keep existing assets</option>
              <option value="true">Replace existing assets</option>
            </select>
          </div>
          <div class="field">
            <label for="model-acknowledge-approval">Operator Approval</label>
            <select id="model-acknowledge-approval">
              <option value="false" selected>Not acknowledged</option>
              <option value="true">Acknowledged for gated bundle</option>
            </select>
          </div>
          <button id="install-model-bundle">Install Bundle</button>
          <pre id="model-install-response"></pre>
        </div>
      </div>
      <div class="card">
        <h2>Voice Transcription</h2>
        <div class="control-stack">
          <div class="field">
            <label for="voice-transcribe-audio-path">Audio Path</label>
            <input id="voice-transcribe-audio-path" placeholder="C:/path/to/audio.wav" />
          </div>
          <div class="row">
            <div class="field">
              <label for="voice-transcribe-provider">Provider</label>
              <select id="voice-transcribe-provider">
                <option value="whisper">whisper</option>
                <option value="whisper.cpp">whisper.cpp</option>
                <option value="sherpa-onnx">sherpa-onnx</option>
              </select>
            </div>
            <div class="field">
              <label for="voice-transcribe-model">Model</label>
              <input id="voice-transcribe-model" value="base" placeholder="base" />
            </div>
          </div>
          <button id="voice-transcribe-run">Run Transcription</button>
          <pre id="voice-transcribe-response"></pre>
        </div>
      </div>
      <div class="card">
        <h2>Live Perception</h2>
        <pre id="perception-latest"></pre>
        <pre id="perception-history"></pre>
      </div>
      <div class="card">
        <h2>Planner</h2>
        <div class="control-stack">
          <div class="field">
            <label for="planner-goal">Goal</label>
            <textarea id="planner-goal" class="terminal" placeholder="Open notifications and inspect the current app context."></textarea>
          </div>
          <div class="row">
            <div class="field">
              <label for="planner-permissions">Permissions</label>
              <input id="planner-permissions" value="git" placeholder="git,android-control,network" />
            </div>
            <div class="field">
              <label for="planner-auto-execute">Auto Execute</label>
              <select id="planner-auto-execute">
                <option value="false" selected>Plan only</option>
                <option value="true">Plan and execute</option>
              </select>
            </div>
          </div>
          <div class="field">
            <label for="planner-safe-mode">Safe Mode</label>
            <select id="planner-safe-mode">
              <option value="true" selected>Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </div>
          <button id="run-planner">Generate Plan</button>
          <pre id="planner-response"></pre>
          <div class="field">
            <label for="planner-history-select">Historical Plan</label>
            <select id="planner-history-select"></select>
          </div>
          <pre id="planner-history"></pre>
          <pre id="planner-history-detail"></pre>
        </div>
      </div>
      <div class="card">
        <h2>Voice Sessions</h2>
        <div class="control-stack">
          <div class="row">
            <div class="field">
              <label for="voice-session-label">Label</label>
              <input id="voice-session-label" value="dashboard" />
            </div>
            <div class="field">
              <label for="voice-session-background">Background</label>
              <select id="voice-session-background">
                <option value="true" selected>Background</option>
                <option value="false">Foreground</option>
              </select>
            </div>
          </div>
          <button id="start-voice-session">Start Voice Session</button>
          <div class="field">
            <label for="voice-session-select">Active Session</label>
            <select id="voice-session-select"></select>
          </div>
          <div class="field">
            <label for="voice-session-transcript">Transcript Event</label>
            <textarea id="voice-session-transcript" class="terminal" placeholder="Mordecai show notifications"></textarea>
          </div>
          <div class="row">
            <div class="field">
              <label for="voice-session-final">Final Transcript</label>
              <select id="voice-session-final">
                <option value="false">Partial</option>
                <option value="true" selected>Final</option>
              </select>
            </div>
            <div class="field">
              <label for="voice-session-interrupt">Interrupt</label>
              <select id="voice-session-interrupt">
                <option value="false" selected>No</option>
                <option value="true">Yes</option>
              </select>
            </div>
          </div>
          <button id="send-voice-session-event">Send Voice Event</button>
          <pre id="voice-session-response"></pre>
          <pre id="voice-session-list"></pre>
        </div>
      </div>
      <div class="card">
        <h2>Runtime Trace</h2>
        <div id="trace" class="trace-list"></div>
      </div>
      <div class="card">
        <h2>Capabilities Matrix</h2>
        <div id="capabilities" class="cap-grid"></div>
      </div>
      <div class="card">
        <h2>Tool Runner</h2>
        <div class="control-stack">
          <div class="field">
            <label for="tool-name">Tool</label>
            <select id="tool-name"></select>
          </div>
          <div class="row">
            <div class="field">
              <label for="tool-permissions">Permissions</label>
              <input id="tool-permissions" value="git" placeholder="git,llm,network" />
            </div>
            <div class="field">
              <label for="tool-session">Session Id</label>
              <input id="tool-session" value="dashboard" />
            </div>
          </div>
          <div class="row">
            <div class="field">
              <label for="tool-timeout">Timeout Seconds</label>
              <input id="tool-timeout" type="number" min="1" max="60" value="10" />
            </div>
            <div class="field">
              <label for="tool-retries">Retries</label>
              <input id="tool-retries" type="number" min="0" max="3" value="0" />
            </div>
          </div>
          <div class="field">
            <label for="tool-safe-mode">Safe Mode</label>
            <select id="tool-safe-mode">
              <option value="true" selected>Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </div>
          <div class="field">
            <label for="tool-arguments">Arguments JSON</label>
            <textarea id="tool-arguments" class="terminal">{}</textarea>
          </div>
          <button id="run-tool">Execute Tool</button>
          <pre id="tool-response"></pre>
        </div>
      </div>
      <div class="card">
        <h2>Execution History</h2>
        <div id="execution-history" class="trace-list"></div>
      </div>
    </section>
  </div>
  <script>
    let latestCapabilities = null;
    let latestVoiceFilter = {};
    let selectedPlanId = '';

    function summarizePerception(snapshot) {
      if (!snapshot || Object.keys(snapshot).length === 0) {
        return { status: 'No perception snapshot yet.' };
      }
      return {
        snapshot_id: snapshot.snapshot_id,
        app_package: snapshot.app_package,
        activity: snapshot.activity,
        screen_title: snapshot.screen_title,
        focused_text: snapshot.focused_text,
        visible_text: (snapshot.visible_text || []).slice(0, 12),
        action_labels: (snapshot.action_labels || []).slice(0, 12),
        notification_summaries: (snapshot.notification_summaries || []).slice(0, 8),
      };
    }

    function readVoiceFilter() {
      return {
        query: document.getElementById('voice-query').value.trim(),
        category: document.getElementById('voice-category').value,
        runtime_fit: document.getElementById('voice-runtime-fit').value,
        supported_only: document.getElementById('voice-supported-only').value,
      };
    }

    function buildVoiceCatalogUrl() {
      const params = new URLSearchParams();
      const filter = latestVoiceFilter;
      if (filter.query) params.set('query', filter.query);
      if (filter.category) params.set('category', filter.category);
      if (filter.runtime_fit) params.set('runtime_fit', filter.runtime_fit);
      if (filter.supported_only === 'true') params.set('supported_only', 'true');
      const queryString = params.toString();
      return queryString ? `/api/voice/catalog?${queryString}` : '/api/voice/catalog';
    }

    async function loadSelectedPlanDetail() {
      const target = document.getElementById('planner-history-detail');
      if (!selectedPlanId) {
        target.textContent = JSON.stringify({ status: 'No historical plan selected.' }, null, 2);
        return;
      }
      const response = await fetch(`/api/agent/plans/${selectedPlanId}`);
      const payload = await response.json();
      target.textContent = JSON.stringify(payload, null, 2);
    }

    async function load() {
      const [status, policy, memory, gitState, candidates, goals, routines, events, proxyLogs, localModels, voiceCatalog, trace, capabilities, avatar, perceptionLatest, perceptionHistory, voiceSessions, planHistory] = await Promise.all([
        fetch('/api/status').then(r => r.json()),
        fetch('/api/policy').then(r => r.json()),
        fetch('/api/memory').then(r => r.json()),
        fetch('/api/git/status').then(r => r.json()),
        fetch('/api/improvement/candidates').then(r => r.json()),
        fetch('/api/goals').then(r => r.json()),
        fetch('/api/routines').then(r => r.json()),
        fetch('/api/events').then(r => r.json()),
        fetch('/api/proxy/logs').then(r => r.json()),
        fetch('/api/local-models').then(r => r.json()),
        fetch(buildVoiceCatalogUrl()).then(r => r.json()),
        fetch('/api/runtime/trace').then(r => r.json()),
        fetch('/api/runtime/capabilities').then(r => r.json()),
        fetch('/api/avatar').then(r => r.json()),
        fetch('/api/android/perception/latest').then(r => r.json()),
        fetch('/api/android/perception/history').then(r => r.json()),
        fetch('/api/voice/sessions').then(r => r.json()),
        fetch('/api/agent/plans').then(r => r.json()),
      ]);
      latestCapabilities = capabilities;

      document.getElementById('metrics').innerHTML = `
        <div class="metric"><div class="label">Provider</div><div class="value">${status.provider}</div></div>
        <div class="metric"><div class="label">CPU</div><div class="value">${status.cpu_percent.toFixed(1)}%</div></div>
        <div class="metric"><div class="label">Memory</div><div class="value">${status.memory_mb.toFixed(1)} MB</div></div>
        <div class="metric"><div class="label">Pending</div><div class="value">${status.pending_candidates}</div></div>
        <div class="metric"><div class="label">Goals</div><div class="value">${status.active_goals}</div></div>
        <div class="metric"><div class="label">Routines</div><div class="value">${status.active_routines}</div></div>`;

      document.getElementById('wake-words').innerHTML = status.wake_words.map(word => `<span class="tag">${word}</span>`).join('');
      const currentFrame = avatar.frames.find(frame => frame.emotion === avatar.current_emotion) || avatar.frames[0];
      document.getElementById('avatar-frame').innerHTML = currentFrame ? currentFrame.svg : '';
      document.getElementById('avatar-meta').textContent = `${avatar.style} | emotion=${avatar.current_emotion} | immutable assets=${avatar.immutable_assets}`;
      document.getElementById('policy').textContent = JSON.stringify(policy, null, 2);
      document.getElementById('memory').textContent = JSON.stringify(memory.slice(-20), null, 2);
      document.getElementById('git').textContent = JSON.stringify(gitState, null, 2);
      document.getElementById('candidates').textContent = JSON.stringify(candidates, null, 2);
      document.getElementById('goals').textContent = JSON.stringify(goals, null, 2);
      document.getElementById('routines').textContent = JSON.stringify(routines, null, 2);
      document.getElementById('events').textContent = JSON.stringify(events.slice(-10), null, 2);
      document.getElementById('proxy').textContent = JSON.stringify(proxyLogs.slice(-10), null, 2);
      document.getElementById('local-models').textContent = JSON.stringify(localModels, null, 2);
      document.getElementById('perception-latest').textContent = JSON.stringify(summarizePerception(perceptionLatest), null, 2);
      document.getElementById('perception-history').textContent = JSON.stringify((perceptionHistory || []).slice(-5).map(summarizePerception), null, 2);
      document.getElementById('voice-session-list').textContent = JSON.stringify((voiceSessions || []).slice(-10), null, 2);
      document.getElementById('planner-history').textContent = JSON.stringify((planHistory || []).slice(-10).reverse().map(plan => ({
        plan_id: plan.plan_id,
        session_id: plan.session_id,
        goal: plan.goal,
        executed: plan.executed,
        created_at: plan.created_at,
        step_count: (plan.steps || []).length,
        final_response: plan.final_response,
      })), null, 2);
      const planSelect = document.getElementById('planner-history-select');
      const sortedPlans = (planHistory || []).slice().reverse();
      const currentPlan = selectedPlanId;
      planSelect.innerHTML = sortedPlans.map(plan => `<option value="${plan.plan_id}">${plan.goal} | ${plan.executed ? 'executed' : 'planned'} | ${plan.plan_id}</option>`).join('');
      if (currentPlan && sortedPlans.some(plan => plan.plan_id === currentPlan)) {
        planSelect.value = currentPlan;
      }
      if (!planSelect.value && planSelect.options.length > 0) {
        planSelect.selectedIndex = 0;
      }
      selectedPlanId = planSelect.value || '';
      await loadSelectedPlanDetail();
      document.getElementById('voice-catalog').textContent = JSON.stringify({
        summary: voiceCatalog.summary,
        filters: voiceCatalog.filters,
        recommended_stack: voiceCatalog.recommended_stack,
        category_preview: (voiceCatalog.categories || []).map(category => ({
          id: category.id,
          label: category.label,
          count: category.count,
        })),
        repo_preview: (voiceCatalog.repos || []).slice(0, 12).map(repo => ({
          slug: repo.slug,
          name: repo.name,
          runtime_fit: repo.runtime_fit,
          integration_tier: repo.integration_tier,
          supported_by_runtime: repo.supported_by_runtime,
        })),
      }, null, 2);
      const bundleSelect = document.getElementById('model-bundle');
      const currentBundle = bundleSelect.value;
      bundleSelect.innerHTML = (localModels.bundles || []).map(bundle => {
        const status = `${bundle.installed_assets}/${bundle.total_assets}`;
        return `<option value="${bundle.bundle_id}">${bundle.display_name} (${status})</option>`;
      }).join('');
      if (currentBundle && (localModels.bundles || []).some(bundle => bundle.bundle_id === currentBundle)) {
        bundleSelect.value = currentBundle;
      }
      if (!bundleSelect.value && bundleSelect.options.length > 0) {
        bundleSelect.selectedIndex = 0;
      }
      const selectedBundle = (localModels.bundles || []).find(bundle => bundle.bundle_id === bundleSelect.value) || null;
      document.getElementById('model-bundle-details').textContent = JSON.stringify(selectedBundle, null, 2);
      const approvalSelect = document.getElementById('model-acknowledge-approval');
      if (selectedBundle && selectedBundle.requires_operator_approval) {
        approvalSelect.disabled = false;
      } else {
        approvalSelect.value = 'false';
        approvalSelect.disabled = true;
      }
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
      document.getElementById('execution-history').innerHTML = trace.executions.slice(-8).reverse().map(record => `
        <div class="trace-item">
          <div class="trace-head"><strong>${record.tool_name}</strong><span>${record.status}</span></div>
          <div class="trace-meta">attempts=${record.attempts} | duration=${record.duration_ms.toFixed(2)}ms</div>
          <pre>${JSON.stringify(record, null, 2)}</pre>
        </div>
      `).join('') || '<div class="trace-item">No recorded tool executions yet.</div>';

      const toolSelect = document.getElementById('tool-name');
      const currentTool = toolSelect.value;
      toolSelect.innerHTML = capabilities.tools.map(tool => `<option value="${tool.tool}">${tool.tool}</option>`).join('');
      if (currentTool && capabilities.tools.some(tool => tool.tool === currentTool)) {
        toolSelect.value = currentTool;
      }

      const sessionSelect = document.getElementById('voice-session-select');
      const currentSession = sessionSelect.value;
      sessionSelect.innerHTML = (voiceSessions || []).map(session => `<option value="${session.session_id}">${session.label} | ${session.status} | ${session.session_id}</option>`).join('');
      if (currentSession && (voiceSessions || []).some(session => session.session_id === currentSession)) {
        sessionSelect.value = currentSession;
      }
      if (!sessionSelect.value && sessionSelect.options.length > 0) {
        sessionSelect.selectedIndex = 0;
      }
      updateToolDefaults();
    }

    function updateToolDefaults() {
      if (!latestCapabilities) {
        return;
      }
      const toolName = document.getElementById('tool-name').value;
      const tool = latestCapabilities.tools.find(item => item.tool === toolName);
      if (!tool) {
        return;
      }
      document.getElementById('tool-permissions').value = tool.permissions.join(',');
      const defaults = {};
      for (const [key, value] of Object.entries(tool.input_schema)) {
        if (value === 'array') {
          defaults[key] = [];
        } else if (value === 'boolean') {
          defaults[key] = false;
        } else if (value === 'integer') {
          defaults[key] = 0;
        } else {
          defaults[key] = '';
        }
      }
      document.getElementById('tool-arguments').value = JSON.stringify(defaults, null, 2);
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

    document.getElementById('tool-name').addEventListener('change', updateToolDefaults);

    document.getElementById('apply-voice-filters').addEventListener('click', async () => {
      latestVoiceFilter = readVoiceFilter();
      await load();
    });

    document.getElementById('model-bundle').addEventListener('change', async () => {
      await load();
    });

    document.getElementById('planner-history-select').addEventListener('change', async event => {
      selectedPlanId = event.target.value;
      await loadSelectedPlanDetail();
    });

    document.getElementById('install-model-bundle').addEventListener('click', async () => {
      const bundleId = document.getElementById('model-bundle').value;
      const overwrite = document.getElementById('model-overwrite').value === 'true';
      const acknowledgeOperatorApproval = document.getElementById('model-acknowledge-approval').value === 'true';
      if (!bundleId) {
        document.getElementById('model-install-response').textContent = JSON.stringify({ error: 'No bundle is available.' }, null, 2);
        return;
      }
      const response = await fetch('/api/local-models/install', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bundle_id: bundleId, overwrite, acknowledge_operator_approval: acknowledgeOperatorApproval }),
      });
      const payload = await response.json();
      document.getElementById('model-install-response').textContent = JSON.stringify(payload, null, 2);
      await load();
    });

    document.getElementById('voice-transcribe-run').addEventListener('click', async () => {
      const audioPath = document.getElementById('voice-transcribe-audio-path').value.trim();
      const provider = document.getElementById('voice-transcribe-provider').value;
      const model = document.getElementById('voice-transcribe-model').value.trim() || 'base';
      if (!audioPath) {
        document.getElementById('voice-transcribe-response').textContent = JSON.stringify({ error: 'Audio path is required.' }, null, 2);
        return;
      }
      const response = await fetch('/api/voice/transcribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio_path: audioPath, provider, model }),
      });
      const payload = await response.json();
      document.getElementById('voice-transcribe-response').textContent = JSON.stringify(payload, null, 2);
      await load();
    });

    document.getElementById('run-planner').addEventListener('click', async () => {
      const goal = document.getElementById('planner-goal').value.trim();
      if (!goal) {
        document.getElementById('planner-response').textContent = JSON.stringify({ error: 'Goal is required.' }, null, 2);
        return;
      }
      const response = await fetch('/api/agent/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal,
          auto_execute: document.getElementById('planner-auto-execute').value === 'true',
          granted_permissions: document.getElementById('planner-permissions').value.split(',').map(item => item.trim()).filter(Boolean),
          safe_mode: document.getElementById('planner-safe-mode').value === 'true',
        }),
      });
      const payload = await response.json();
      document.getElementById('planner-response').textContent = JSON.stringify(payload, null, 2);
      selectedPlanId = payload.plan_id || selectedPlanId;
      await load();
    });

    document.getElementById('start-voice-session').addEventListener('click', async () => {
      const response = await fetch('/api/voice/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: document.getElementById('voice-session-label').value.trim() || 'dashboard',
          background: document.getElementById('voice-session-background').value === 'true',
        }),
      });
      const payload = await response.json();
      document.getElementById('voice-session-response').textContent = JSON.stringify(payload, null, 2);
      await load();
      if (payload.session_id) {
        document.getElementById('voice-session-select').value = payload.session_id;
      }
    });

    document.getElementById('send-voice-session-event').addEventListener('click', async () => {
      const sessionId = document.getElementById('voice-session-select').value;
      if (!sessionId) {
        document.getElementById('voice-session-response').textContent = JSON.stringify({ error: 'Start or select a voice session first.' }, null, 2);
        return;
      }
      const response = await fetch(`/api/voice/sessions/${sessionId}/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: document.getElementById('voice-session-transcript').value,
          is_final: document.getElementById('voice-session-final').value === 'true',
          interrupt: document.getElementById('voice-session-interrupt').value === 'true',
          auto_execute: true,
        }),
      });
      const payload = await response.json();
      document.getElementById('voice-session-response').textContent = JSON.stringify(payload, null, 2);
      await load();
    });

    document.getElementById('run-tool').addEventListener('click', async () => {
      let argumentsPayload = {};
      try {
        argumentsPayload = JSON.parse(document.getElementById('tool-arguments').value || '{}');
      } catch (error) {
        document.getElementById('tool-response').textContent = JSON.stringify({ error: 'Arguments must be valid JSON.' }, null, 2);
        return;
      }
      const response = await fetch('/api/tools/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: document.getElementById('tool-name').value,
          arguments: argumentsPayload,
          granted_permissions: document.getElementById('tool-permissions').value.split(',').map(item => item.trim()).filter(Boolean),
          session_id: document.getElementById('tool-session').value,
          timeout_seconds: Number(document.getElementById('tool-timeout').value),
          max_retries: Number(document.getElementById('tool-retries').value),
          safe_mode: document.getElementById('tool-safe-mode').value === 'true',
        }),
      });
      const payload = await response.json();
      document.getElementById('tool-response').textContent = JSON.stringify(payload, null, 2);
      await load();
    });

    load();
  </script>
</body>
</html>
"""