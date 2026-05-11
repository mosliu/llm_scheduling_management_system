HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Workflow Task Studio</title>
  <style>
    :root {
      --bg: #f6efe3;
      --panel: #fffaf2;
      --panel-2: #fcf5ea;
      --ink: #1b1a17;
      --muted: #6e6559;
      --line: #d9c9b1;
      --accent: #b2482b;
      --accent-2: #1d5a4f;
      --accent-3: #9b7f2c;
      --danger: #8f2f2f;
      --ok: #2f7d4f;
      --shadow: 0 18px 40px rgba(41, 31, 18, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top left, rgba(178,72,43,.14), transparent 30%),
        radial-gradient(circle at bottom right, rgba(29,90,79,.12), transparent 35%),
        linear-gradient(180deg, #faf5eb 0%, var(--bg) 100%);
    }
    .page { max-width: 1520px; margin: 0 auto; padding: 26px; }
    .hero { display: grid; grid-template-columns: 1.35fr .65fr; gap: 18px; margin-bottom: 20px; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: var(--shadow);
      padding: 18px;
    }
    .panel.alt { background: var(--panel-2); }
    h1, h2, h3 { margin: 0 0 10px; letter-spacing: -.02em; }
    h1 { font-size: 42px; line-height: 1; }
    h2 { font-size: 24px; }
    h3 { font-size: 18px; }
    .muted { color: var(--muted); }
    .badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
    .badge {
      border-radius: 999px;
      border: 1px solid var(--line);
      padding: 6px 10px;
      font-size: 12px;
      color: var(--muted);
      background: rgba(255,255,255,.6);
    }
    .tabs { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 18px; }
    .tab-button {
      border: 1px solid var(--line);
      background: rgba(255,255,255,.65);
      border-radius: 999px;
      padding: 10px 14px;
      font-weight: 700;
      cursor: pointer;
    }
    .tab-button.active { background: var(--ink); color: white; border-color: var(--ink); }
    .tab-pane { display: none; }
    .tab-pane.active { display: block; }
    .grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 18px; }
    .span-3 { grid-column: span 3; }
    .span-4 { grid-column: span 4; }
    .span-5 { grid-column: span 5; }
    .span-6 { grid-column: span 6; }
    .span-7 { grid-column: span 7; }
    .span-8 { grid-column: span 8; }
    .span-12 { grid-column: span 12; }
    .stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
    .stat {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: rgba(255,255,255,.55);
    }
    .stat .label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }
    .stat .value { font-size: 28px; font-weight: 700; margin-top: 4px; }
    .row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 12px; }
    label { display: block; font-size: 13px; font-weight: 700; margin-bottom: 6px; }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 11px 12px;
      background: #fffefb;
      color: var(--ink);
      font: inherit;
    }
    textarea { min-height: 120px; font: 13px/1.45 Consolas, "Courier New", monospace; resize: vertical; }
    select[multiple] { min-height: 110px; font-size: 13px; }
    button {
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      font-weight: 700;
      cursor: pointer;
      color: white;
      background: var(--accent);
    }
    button.secondary { background: var(--accent-2); }
    button.warning { background: var(--accent-3); }
    button.danger { background: var(--danger); }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
    .task-list, .list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-height: 760px;
      overflow: auto;
      padding-right: 4px;
    }
    .list { max-height: 340px; }
    .task-card, .list-item {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: rgba(255,255,255,.55);
    }
    .task-card { cursor: pointer; }
    .task-card.active { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
    .task-head { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
    .pill {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 11px;
      color: var(--muted);
      background: #fffefb;
    }
    .codebox, pre {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fffefb;
      padding: 12px;
      overflow: auto;
      white-space: pre-wrap;
      font: 12px/1.45 Consolas, "Courier New", monospace;
    }
    .message { margin-top: 10px; font-size: 13px; color: var(--muted); }
    .health-ok { color: var(--ok); font-weight: 700; }
    .health-bad { color: var(--danger); font-weight: 700; }
    .graph-canvas {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fffefb;
      padding: 12px;
      min-height: 260px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }
    .graph-node {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
      background: rgba(255,255,255,.7);
    }
    .graph-node.step { border-left: 5px solid var(--accent); }
    .graph-node.artifact { border-left: 5px solid var(--accent-2); }
    @media (max-width: 1180px) {
      .hero, .stats, .row { grid-template-columns: 1fr; }
      .span-3, .span-4, .span-5, .span-6, .span-7, .span-8, .span-12 { grid-column: span 12; }
    }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="panel">
        <h1>Workflow Task Studio</h1>
        <p class="muted">Operate workflows, configure providers, inspect artifacts, and control execution from one local console.</p>
        <div class="badges">
          <span class="badge">Task Control</span>
          <span class="badge">Provider Config</span>
          <span class="badge">Search / Fetch / LLM / MCP</span>
          <span class="badge">Graph / Events / Bundle</span>
        </div>
      </div>
      <div class="panel alt">
        <h3>Model Notes</h3>
        <p class="muted">Load compatibility notes for Grok and Claude relay models.</p>
        <div class="actions">
          <button class="secondary" onclick="loadGrokNote()">Load Grok Note</button>
          <button class="secondary" onclick="loadClaudeNote()">Load Claude Note</button>
        </div>
        <pre id="modelNotes" class="codebox"></pre>
      </div>
    </section>

    <div class="tabs">
      <button class="tab-button active" onclick="setTab('overview', this)">Overview</button>
      <button class="tab-button" onclick="setTab('tasks', this)">Tasks</button>
      <button class="tab-button" onclick="setTab('detail', this)">Selected Task</button>
      <button class="tab-button" onclick="setTab('config', this)">Config</button>
    </div>

    <section id="tab-overview" class="tab-pane active">
      <div class="panel">
        <h2>System Status</h2>
        <div class="stats">
          <div class="stat"><div class="label">Templates</div><div class="value" id="statTemplates">-</div></div>
          <div class="stat"><div class="label">Tasks</div><div class="value" id="statTasks">-</div></div>
          <div class="stat"><div class="label">Search Providers</div><div class="value" id="statSearchProviders">-</div></div>
          <div class="stat"><div class="label">LLM Profiles</div><div class="value" id="statLLMProfiles">-</div></div>
        </div>
        <div class="message" id="systemMessage"></div>
      </div>
      <div class="grid" style="margin-top:18px;">
        <div class="span-6 panel">
          <h2>Provider Snapshot</h2>
          <pre id="providerSnapshot" class="codebox"></pre>
        </div>
        <div class="span-6 panel">
          <h2>Provider Health</h2>
          <div class="actions">
            <button class="secondary" onclick="loadProviderHealth()">Run Health Checks</button>
          </div>
          <div class="list" id="providerHealth"></div>
        </div>
      </div>
    </section>

    <section id="tab-tasks" class="tab-pane">
      <div class="grid">
        <div class="span-5 panel">
          <h2>Create Task</h2>
          <div class="row">
            <div>
              <label for="templateSelect">Workflow Template</label>
              <select id="templateSelect"></select>
            </div>
            <div>
              <label for="topicInput">Topic</label>
              <input id="topicInput" placeholder="latest AI agent news" />
            </div>
          </div>
          <div class="row">
            <div>
              <label for="searchProvidersSelect">Search Providers</label>
              <select id="searchProvidersSelect" multiple size="4"></select>
            </div>
            <div>
              <label for="fetchProviderSelect">Fetch Provider</label>
              <select id="fetchProviderSelect"></select>
            </div>
          </div>
          <div class="row">
            <div>
              <label for="llmProfileSelect">LLM Profile</label>
              <select id="llmProfileSelect"></select>
            </div>
            <div>
              <label for="executionEngineSelect">Execution Engine</label>
              <select id="executionEngineSelect">
                <option value="">native</option>
                <option value="langgraph">langgraph</option>
              </select>
            </div>
          </div>
          <div class="row">
            <div>
              <label for="taskTenantInput">Tenant</label>
              <input id="taskTenantInput" value="default" />
            </div>
            <div></div>
          </div>
          <div class="row">
            <div>
              <label for="startInput">Time Range Start</label>
              <input id="startInput" placeholder="2026-05-01T00:00:00Z" />
            </div>
            <div>
              <label for="endInput">Time Range End</label>
              <input id="endInput" placeholder="2026-05-09T00:00:00Z" />
            </div>
          </div>
          <label for="inputJson">Additional Input JSON</label>
          <textarea id="inputJson">{}</textarea>
          <label for="optionsJson">Options JSON</label>
          <textarea id="optionsJson">{"disable_cache": false}</textarea>
          <div class="actions">
            <button onclick="createTask()">Create Task</button>
            <button class="secondary" onclick="loadTemplates()">Reload Templates</button>
          </div>
          <div class="message" id="createTaskMessage"></div>
        </div>

        <div class="span-7 panel">
          <h2>Task List</h2>
          <div class="row">
            <div>
              <label for="taskStatusFilter">Status Filter</label>
              <select id="taskStatusFilter">
                <option value="">All</option>
                <option value="queued">queued</option>
                <option value="running">running</option>
                <option value="waiting_retry">waiting_retry</option>
                <option value="succeeded">succeeded</option>
                <option value="cancelled">cancelled</option>
                <option value="partial_failed">partial_failed</option>
                <option value="failed">failed</option>
              </select>
            </div>
            <div>
              <label for="taskTemplateFilter">Template Filter</label>
              <select id="taskTemplateFilter">
                <option value="">All</option>
              </select>
            </div>
          </div>
          <div class="actions">
            <button class="secondary" onclick="loadTasks()">Refresh Tasks</button>
            <button class="warning" id="autoRefreshButton" onclick="toggleAutoRefresh()">Auto Refresh: Off</button>
          </div>
          <div class="task-list" id="taskList"></div>
        </div>
      </div>
    </section>

    <section id="tab-detail" class="tab-pane">
      <div class="grid">
        <div class="span-12 panel">
          <div style="display:flex;justify-content:space-between;gap:20px;align-items:flex-start;flex-wrap:wrap;">
            <div>
              <h2 id="detailTitle">No Task Selected</h2>
              <p class="muted" id="detailMeta">Select a task from the Tasks tab.</p>
            </div>
            <div class="actions">
              <button onclick="runSelectedTask()">Run All</button>
              <button class="secondary" onclick="runNextSelectedTaskStep()">Run Next Step</button>
              <button class="warning" onclick="refreshSelectedTask()">Refresh</button>
              <button class="danger" onclick="cancelSelectedTask()">Cancel</button>
            </div>
          </div>
        </div>

        <div class="span-4 panel"><h3>Summary</h3><pre id="detailSummary" class="codebox"></pre></div>
        <div class="span-4 panel"><h3>Stats</h3><pre id="detailStats" class="codebox"></pre></div>
        <div class="span-4 panel">
          <h3>Graph</h3>
          <div id="detailGraphCanvas" class="graph-canvas"></div>
        </div>

        <div class="span-6 panel"><h3>Steps</h3><div class="list" id="detailSteps"></div></div>
        <div class="span-6 panel"><h3>Events</h3><div class="list" id="detailEvents"></div></div>
        <div class="span-6 panel"><h3>Search Hits</h3><div class="list" id="detailHits"></div></div>
        <div class="span-6 panel"><h3>Documents</h3><div class="list" id="detailDocuments"></div></div>
        <div class="span-6 panel"><h3>Artifacts</h3><div class="list" id="detailArtifacts"></div></div>
        <div class="span-6 panel"><h3>Checkpoints</h3><div class="list" id="detailCheckpoints"></div></div>
        <div class="span-3 panel"><h3>Search Invocations</h3><div class="list" id="detailSearchInvocations"></div></div>
        <div class="span-3 panel"><h3>Fetch Invocations</h3><div class="list" id="detailFetchInvocations"></div></div>
        <div class="span-3 panel"><h3>Tool Invocations</h3><div class="list" id="detailToolInvocations"></div></div>
        <div class="span-3 panel"><h3>LLM Invocations</h3><div class="list" id="detailLlmInvocations"></div></div>

        <div class="span-12 panel">
          <h3>Task Bundle</h3>
          <div class="actions">
            <button class="secondary" onclick="downloadBundle()">Download Bundle JSON</button>
          </div>
          <pre id="detailBundle" class="codebox"></pre>
        </div>

        <div class="span-12 panel">
          <h3>Continuation Tools</h3>
          <p class="muted" id="continuationSelection">No step, artifact, or checkpoint selected.</p>
          <div class="row">
            <div>
              <label for="continuationTemplateSelect">Target Template</label>
              <select id="continuationTemplateSelect"></select>
            </div>
            <div>
              <label for="continuationTenantInput">Tenant</label>
              <input id="continuationTenantInput" value="default" />
            </div>
          </div>
          <label for="continuationInputJson">Continuation Input JSON</label>
          <textarea id="continuationInputJson">{}</textarea>
          <label for="continuationOptionsJson">Continuation Options JSON</label>
          <textarea id="continuationOptionsJson">{"disable_cache": false}</textarea>
          <div class="actions">
            <button class="secondary" onclick="deriveTaskFromSelectedStep()">Derive Task from Step</button>
            <button class="secondary" onclick="resumeTaskFromSelectedArtifact()">Resume from Artifact</button>
            <button class="secondary" onclick="resumeTaskFromSelectedCheckpoint()">Resume from Checkpoint</button>
          </div>
          <div class="message" id="continuationMessage"></div>
        </div>
      </div>
    </section>

    <section id="tab-config" class="tab-pane">
      <div class="grid">
        <div class="span-6 panel">
          <h2>Search Config</h2>
          <p class="muted" id="searchPath"></p>
          <textarea id="searchConfig"></textarea>
          <div class="actions">
            <button onclick="loadConfig('search')">Reload</button>
            <button onclick="saveConfig('search')">Save</button>
            <button class="secondary" onclick="testConfig('search')">Test Search Config</button>
          </div>
        </div>
        <div class="span-6 panel">
          <h2>LLM Config</h2>
          <p class="muted" id="llmPath"></p>
          <textarea id="llmConfig"></textarea>
          <div class="actions">
            <button onclick="loadConfig('llm')">Reload</button>
            <button onclick="saveConfig('llm')">Save</button>
            <button class="secondary" onclick="testConfig('llm')">Test LLM Config</button>
          </div>
        </div>
        <div class="span-6 panel">
          <h2>Source Registry</h2>
          <p class="muted" id="registryPath"></p>
          <textarea id="registryConfig"></textarea>
          <div class="actions">
            <button onclick="loadConfig('source-registry')">Reload</button>
            <button onclick="saveConfig('source-registry')">Save</button>
          </div>
        </div>
        <div class="span-6 panel">
          <h2>MCP Config</h2>
          <p class="muted" id="mcpPath"></p>
          <textarea id="mcpConfig"></textarea>
          <div class="actions">
            <button onclick="loadConfig('mcp')">Reload</button>
            <button onclick="saveConfig('mcp')">Save</button>
            <button class="secondary" onclick="testConfig('mcp')">Test MCP Config</button>
          </div>
        </div>
        <div class="span-12 panel">
          <h2>Catalog Snapshot</h2>
          <div class="actions">
            <button class="secondary" onclick="loadCatalog()">Refresh Snapshot</button>
          </div>
          <pre id="catalog" class="codebox"></pre>
          <div class="message" id="configTestMessage"></div>
        </div>
      </div>
    </section>
  </div>

  <script>
    const state = {
      selectedTaskId: null,
      selectedStepId: null,
      selectedArtifactId: null,
      selectedCheckpointId: null,
      tasks: [],
      templates: [],
      bundle: null,
      autoRefresh: false,
      autoRefreshTimer: null,
    };

    function setTab(name, button) {
      document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
      button.classList.add('active');
      document.getElementById(`tab-${name}`).classList.add('active');
    }

    function pretty(value) {
      return JSON.stringify(value, null, 2);
    }

    async function api(url, options) {
      const response = await fetch(url, options);
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
      }
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        return await response.json();
      }
      return await response.text();
    }

    function renderList(containerId, items, formatter) {
      const container = document.getElementById(containerId);
      container.innerHTML = '';
      if (!items || !items.length) {
        container.innerHTML = '<div class="list-item muted">No data.</div>';
        return;
      }
      for (const item of items) {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = formatter(item);
        container.appendChild(div);
      }
    }

    function renderGraph(graph) {
      const container = document.getElementById('detailGraphCanvas');
      container.innerHTML = '';
      if (!graph || !graph.nodes || !graph.nodes.length) {
        container.innerHTML = '<div class="graph-node muted">No graph data.</div>';
        return;
      }
      for (const node of graph.nodes) {
        const div = document.createElement('div');
        div.className = `graph-node ${node.node_kind}`;
        div.innerHTML = `
          <strong>${node.label}</strong>
          <div class="muted">${node.node_kind}${node.status ? ` · ${node.status}` : ''}</div>
          <div class="muted">${JSON.stringify(node.metadata || {})}</div>
        `;
        container.appendChild(div);
      }
    }

    function toggleAutoRefresh() {
      state.autoRefresh = !state.autoRefresh;
      const button = document.getElementById('autoRefreshButton');
      button.textContent = state.autoRefresh ? 'Auto Refresh: On' : 'Auto Refresh: Off';
      if (state.autoRefresh) {
        state.autoRefreshTimer = setInterval(async () => {
          await loadTasks();
          await loadSystemStatus();
          if (state.selectedTaskId) {
            await refreshSelectedTask();
          }
        }, 5000);
      } else if (state.autoRefreshTimer) {
        clearInterval(state.autoRefreshTimer);
        state.autoRefreshTimer = null;
      }
    }

    async function loadSystemStatus() {
      const data = await api('/api/v1/system/status');
      document.getElementById('statTemplates').textContent = data.template_count;
      document.getElementById('statTasks').textContent = data.total_tasks;
      document.getElementById('statSearchProviders').textContent = data.provider_counts.search;
      document.getElementById('statLLMProfiles').textContent = data.provider_counts.llm_profiles;
      document.getElementById('systemMessage').textContent = `Task statuses: ${pretty(data.task_status_counts)}`;
    }

    async function loadTemplates() {
      const data = await api('/api/v1/workflow-templates');
      state.templates = data;
      const templateSelect = document.getElementById('templateSelect');
      const continuationSelect = document.getElementById('continuationTemplateSelect');
      const taskFilter = document.getElementById('taskTemplateFilter');
      templateSelect.innerHTML = '';
      continuationSelect.innerHTML = '';
      taskFilter.innerHTML = '<option value="">All</option>';
      for (const item of data) {
        const option = document.createElement('option');
        option.value = item.template_id;
        option.textContent = `${item.template_id} — ${item.name}`;
        templateSelect.appendChild(option);

        const continuationOption = document.createElement('option');
        continuationOption.value = item.template_id;
        continuationOption.textContent = `${item.template_id} — ${item.name}`;
        continuationSelect.appendChild(continuationOption);

        const filterOption = document.createElement('option');
        filterOption.value = item.template_id;
        filterOption.textContent = item.template_id;
        taskFilter.appendChild(filterOption);
      }
      await loadProviderSelectors();
    }

    async function loadProviderSelectors() {
      const [searchProviders, fetchProviders, llmProfiles] = await Promise.all([
        api('/api/v1/provider-catalog/search'),
        api('/api/v1/provider-catalog/fetch'),
        api('/api/v1/provider-catalog/llm/profiles'),
      ]);
      const searchSelect = document.getElementById('searchProvidersSelect');
      const fetchSelect = document.getElementById('fetchProviderSelect');
      const llmSelect = document.getElementById('llmProfileSelect');
      searchSelect.innerHTML = '';
      fetchSelect.innerHTML = '';
      llmSelect.innerHTML = '';
      for (const item of searchProviders) {
        const option = document.createElement('option');
        option.value = item.name;
        option.textContent = `${item.name} (${item.vendor})`;
        if (item.enabled) option.selected = true;
        searchSelect.appendChild(option);
      }
      for (const item of fetchProviders) {
        const option = document.createElement('option');
        option.value = item.name;
        option.textContent = `${item.name} (${item.vendor})`;
        fetchSelect.appendChild(option);
      }
      for (const item of llmProfiles) {
        const option = document.createElement('option');
        option.value = item.name;
        option.textContent = `${item.name} → ${item.model}`;
        llmSelect.appendChild(option);
      }
    }

    async function loadTasks() {
      const status = document.getElementById('taskStatusFilter').value;
      const templateId = document.getElementById('taskTemplateFilter').value;
      const params = new URLSearchParams();
      if (status) params.set('status', status);
      if (templateId) params.set('template_id', templateId);
      params.set('limit', '100');
      const data = await api(`/api/v1/tasks?${params.toString()}`);
      state.tasks = data;
      const container = document.getElementById('taskList');
      container.innerHTML = '';
      if (!data.length) {
        container.innerHTML = '<div class="task-card muted">No tasks yet.</div>';
        return;
      }
      for (const item of data) {
        const card = document.createElement('div');
        card.className = 'task-card' + (state.selectedTaskId === item.task_id ? ' active' : '');
        card.onclick = () => selectTask(item.task_id);
        card.innerHTML = `
          <div class="task-head">
            <strong>${item.task_id}</strong>
            <span class="pill">${item.status}</span>
          </div>
          <div class="muted">${item.template_id}</div>
          <div class="muted">Progress ${item.progress}% · ${item.completed_step_count}/${item.planned_step_count}</div>
        `;
        container.appendChild(card);
      }
    }

    async function createTask() {
      const templateId = document.getElementById('templateSelect').value;
      const topic = document.getElementById('topicInput').value.trim();
      const tenantId = document.getElementById('taskTenantInput').value.trim() || 'default';
      const start = document.getElementById('startInput').value.trim();
      const end = document.getElementById('endInput').value.trim();
      const extraInput = JSON.parse(document.getElementById('inputJson').value || '{}');
      const options = JSON.parse(document.getElementById('optionsJson').value || '{}');
      const selectedSearchProviders = Array.from(document.getElementById('searchProvidersSelect').selectedOptions).map(item => item.value);
      const selectedFetchProvider = document.getElementById('fetchProviderSelect').value;
      const selectedLLMProfile = document.getElementById('llmProfileSelect').value;
      const executionEngine = document.getElementById('executionEngineSelect').value;
      const input = { ...extraInput };
      if (topic) input.topic = topic;
      if (start || end) {
        input.time_range = {
          ...(start ? { start } : {}),
          ...(end ? { end } : {}),
        };
      }
      if (selectedSearchProviders.length) options.search_provider_names = selectedSearchProviders;
      if (selectedFetchProvider) options.fetch_provider_name = selectedFetchProvider;
      if (selectedLLMProfile) options.llm_profile_name = selectedLLMProfile;
      if (executionEngine) options.execution_engine = executionEngine;
      const payload = { template_id: templateId, input, options, tenant_id: tenantId };
      const result = await api('/api/v1/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      document.getElementById('createTaskMessage').textContent = `Created ${result.task_id}`;
      await loadTasks();
      await selectTask(result.task_id);
    }

    async function selectTask(taskId) {
      state.selectedTaskId = taskId;
      state.selectedStepId = null;
      state.selectedArtifactId = null;
      state.selectedCheckpointId = null;
      await loadTasks();
      await refreshSelectedTask();
      document.querySelectorAll('.tab-button').forEach(btn => {
        if (btn.textContent === 'Selected Task') btn.click();
      });
    }

    function updateContinuationSelection() {
      const parts = [];
      if (state.selectedStepId) parts.push(`step=${state.selectedStepId}`);
      if (state.selectedArtifactId) parts.push(`artifact=${state.selectedArtifactId}`);
      if (state.selectedCheckpointId) parts.push(`checkpoint=${state.selectedCheckpointId}`);
      document.getElementById('continuationSelection').textContent = parts.length
        ? `Selected: ${parts.join(' | ')}`
        : 'No step, artifact, or checkpoint selected.';
    }

    async function refreshSelectedTask() {
      if (!state.selectedTaskId) return;
      const [task, stats, graph, bundle] = await Promise.all([
        api(`/api/v1/tasks/${state.selectedTaskId}`),
        api(`/api/v1/tasks/${state.selectedTaskId}/stats`),
        api(`/api/v1/tasks/${state.selectedTaskId}/graph`),
        api(`/api/v1/tasks/${state.selectedTaskId}/bundle`),
      ]);
      state.bundle = bundle;
      document.getElementById('detailTitle').textContent = `${task.task_id} · ${task.template_id}`;
      document.getElementById('detailMeta').textContent = `${task.status} · progress ${task.progress}% · current step ${task.current_step || 'n/a'}`;
      document.getElementById('detailSummary').textContent = pretty(task);
      document.getElementById('detailStats').textContent = pretty(stats);
      renderGraph(graph);
      document.getElementById('detailBundle').textContent = pretty(bundle);

      renderList('detailSteps', task.steps, step => `
        <strong>${step.node_key}</strong> <span class="pill">${step.status}</span>
        <div class="muted">${step.title}</div>
        <div class="muted">progress ${step.progress}% · cache ${step.cache_hit}</div>
        <div class="actions"><button class="secondary" onclick="selectStepForContinuation('${step.step_run_id}')">Use Step</button></div>
      `);
      renderList('detailEvents', bundle.events, event => `
        <strong>${event.event_type}</strong> <span class="pill">${event.status || ''}</span>
        <div class="muted">${event.created_at}</div>
        <div class="muted">${JSON.stringify(event.payload)}</div>
      `);
      renderList('detailHits', bundle.search_hits, item => `
        <strong>${item.title}</strong>
        <div class="muted">${item.provider_name} · ${item.source_domain} · ${item.source_type}</div>
        <div class="muted">${item.region_hint || 'unknown'} · ${item.publisher_type || 'unknown'} · ${item.published_at_utc || 'n/a'}</div>
        <div class="muted">${item.snippet || ''}</div>
      `);
      renderList('detailDocuments', bundle.documents, item => `
        <strong>${item.title || item.url}</strong>
        <div class="muted">${item.provider_name} · ${item.source_domain || ''} · ${item.language || ''}</div>
        <div class="muted">${item.region_hint || 'unknown'} · ${item.publisher_type || 'unknown'} · ${item.author || 'unknown author'}</div>
        <div class="muted">${(item.content_text || '').slice(0, 220)}</div>
      `);
      renderList('detailArtifacts', task.artifacts, item => `
        <strong>${item.artifact_type}</strong> <span class="pill">${item.artifact_level}</span>
        <div class="muted">${item.artifact_id}</div>
        <div class="actions"><button class="secondary" onclick="selectArtifactForContinuation('${item.artifact_id}')">Use Artifact</button></div>
      `);
      renderList('detailCheckpoints', task.available_checkpoints, item => `
        <strong>${item.checkpoint_id}</strong>
        <div class="muted">step ${item.based_on_step_run_id || 'n/a'}</div>
        <div class="actions"><button class="secondary" onclick="selectCheckpointForContinuation('${item.checkpoint_id}')">Use Checkpoint</button></div>
      `);
      renderList('detailSearchInvocations', bundle.search_invocations, item => `
        <strong>${item.provider_name}</strong>
        <div class="muted">${item.query_text}</div>
        <div class="muted">results ${item.result_count}</div>
      `);
      renderList('detailFetchInvocations', bundle.fetch_invocations, item => `
        <strong>${item.provider_name}</strong>
        <div class="muted">${item.url}</div>
        <div class="muted">${item.title || ''}</div>
      `);
      renderList('detailToolInvocations', bundle.tool_invocations || [], item => `
        <strong>${item.server_name}</strong>
        <div class="muted">${item.tool_name}</div>
        <div class="muted">${item.status}</div>
      `);
      renderList('detailLlmInvocations', bundle.llm_invocations, item => `
        <strong>${item.provider_name}</strong>
        <div class="muted">${item.model_name} · ${item.profile_name}</div>
        <div class="muted">${(item.response_text || '').slice(0, 220)}</div>
      `);
      updateContinuationSelection();
    }

    async function runSelectedTask() {
      if (!state.selectedTaskId) return;
      await api(`/api/v1/tasks/${state.selectedTaskId}/run`, { method: 'POST' });
      await refreshSelectedTask();
      await loadTasks();
      await loadSystemStatus();
    }

    async function runNextSelectedTaskStep() {
      if (!state.selectedTaskId) return;
      await api(`/api/v1/tasks/${state.selectedTaskId}/run-next-step`, { method: 'POST' });
      await refreshSelectedTask();
      await loadTasks();
      await loadSystemStatus();
    }

    async function cancelSelectedTask() {
      if (!state.selectedTaskId) return;
      await api(`/api/v1/tasks/${state.selectedTaskId}/cancel`, { method: 'POST' });
      await refreshSelectedTask();
      await loadTasks();
      await loadSystemStatus();
    }

    function downloadBundle() {
      if (!state.bundle || !state.selectedTaskId) return;
      const blob = new Blob([JSON.stringify(state.bundle, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${state.selectedTaskId}.bundle.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    }

    function selectStepForContinuation(stepId) {
      state.selectedStepId = stepId;
      updateContinuationSelection();
    }

    function selectArtifactForContinuation(artifactId) {
      state.selectedArtifactId = artifactId;
      updateContinuationSelection();
    }

    function selectCheckpointForContinuation(checkpointId) {
      state.selectedCheckpointId = checkpointId;
      updateContinuationSelection();
    }

    async function deriveTaskFromSelectedStep() {
      if (!state.selectedStepId) {
        document.getElementById('continuationMessage').textContent = 'Select a step first.';
        return;
      }
      const template_id = document.getElementById('continuationTemplateSelect').value;
      const tenant_id = document.getElementById('continuationTenantInput').value.trim() || 'default';
      const input = JSON.parse(document.getElementById('continuationInputJson').value || '{}');
      const options = JSON.parse(document.getElementById('continuationOptionsJson').value || '{}');
      const result = await api(`/api/v1/steps/${state.selectedStepId}/derive-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_id, tenant_id, input, options }),
      });
      document.getElementById('continuationMessage').textContent = `Derived ${result.task_id}`;
      await loadTasks();
      await selectTask(result.task_id);
    }

    async function resumeTaskFromSelectedArtifact() {
      if (!state.selectedArtifactId) {
        document.getElementById('continuationMessage').textContent = 'Select an artifact first.';
        return;
      }
      const template_id = document.getElementById('continuationTemplateSelect').value;
      const tenant_id = document.getElementById('continuationTenantInput').value.trim() || 'default';
      const input = JSON.parse(document.getElementById('continuationInputJson').value || '{}');
      const options = JSON.parse(document.getElementById('continuationOptionsJson').value || '{}');
      const result = await api('/api/v1/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_id, tenant_id, input, options, resume_from: { artifact_id: state.selectedArtifactId } }),
      });
      document.getElementById('continuationMessage').textContent = `Resumed ${result.task_id} from artifact`;
      await loadTasks();
      await selectTask(result.task_id);
    }

    async function resumeTaskFromSelectedCheckpoint() {
      if (!state.selectedCheckpointId) {
        document.getElementById('continuationMessage').textContent = 'Select a checkpoint first.';
        return;
      }
      const template_id = document.getElementById('continuationTemplateSelect').value;
      const tenant_id = document.getElementById('continuationTenantInput').value.trim() || 'default';
      const input = JSON.parse(document.getElementById('continuationInputJson').value || '{}');
      const options = JSON.parse(document.getElementById('continuationOptionsJson').value || '{}');
      const result = await api('/api/v1/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_id, tenant_id, input, options, resume_from: { checkpoint_id: state.selectedCheckpointId } }),
      });
      document.getElementById('continuationMessage').textContent = `Resumed ${result.task_id} from checkpoint`;
      await loadTasks();
      await selectTask(result.task_id);
    }

    async function loadConfig(kind) {
      const payload = await api(`/api/v1/config/${kind}`);
      if (kind === 'search') {
        document.getElementById('searchPath').textContent = payload.path;
        document.getElementById('searchConfig').value = pretty(payload.data);
      } else if (kind === 'llm') {
        document.getElementById('llmPath').textContent = payload.path;
        document.getElementById('llmConfig').value = pretty(payload.data);
      } else if (kind === 'mcp') {
        document.getElementById('mcpPath').textContent = payload.path;
        document.getElementById('mcpConfig').value = pretty(payload.data);
      } else {
        document.getElementById('registryPath').textContent = payload.path;
        document.getElementById('registryConfig').value = pretty(payload.data);
      }
    }

    async function saveConfig(kind) {
      const raw = kind === 'search'
        ? document.getElementById('searchConfig').value
        : kind === 'llm'
          ? document.getElementById('llmConfig').value
          : kind === 'mcp'
            ? document.getElementById('mcpConfig').value
            : document.getElementById('registryConfig').value;
      const payload = await api(`/api/v1/config/${kind}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: JSON.parse(raw) }),
      });
      document.getElementById('configTestMessage').textContent = `Saved ${kind} config to ${payload.path}`;
      await loadCatalog();
      await loadSystemStatus();
    }

    async function testConfig(kind) {
      const raw = kind === 'search'
        ? document.getElementById('searchConfig').value
        : kind === 'llm'
          ? document.getElementById('llmConfig').value
          : document.getElementById('mcpConfig').value;
      const payload = await api(`/api/v1/config/${kind}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: JSON.parse(raw) }),
      });
      document.getElementById('configTestMessage').textContent = pretty(payload);
    }

    async function loadCatalog() {
      const [search, fetchP, crawl, llmP, llmProfiles, registry, mcpServers] = await Promise.all([
        api('/api/v1/provider-catalog/search'),
        api('/api/v1/provider-catalog/fetch'),
        api('/api/v1/provider-catalog/crawl'),
        api('/api/v1/provider-catalog/llm/providers'),
        api('/api/v1/provider-catalog/llm/profiles'),
        api('/api/v1/provider-catalog/source-registry'),
        api('/api/v1/provider-catalog/mcp/servers'),
      ]);
      const snapshot = {
        searchProviders: search,
        fetchProviders: fetchP,
        crawlProviders: crawl,
        llmProviders: llmP,
        llmProfiles,
        sourceRegistry: registry,
        mcpServers,
      };
      document.getElementById('providerSnapshot').textContent = pretty(snapshot);
      document.getElementById('catalog').textContent = pretty(snapshot);
    }

    async function loadProviderHealth() {
      const payload = await api('/api/v1/provider-catalog/health');
      const rows = [];
      for (const group of ['search', 'llm', 'mcp']) {
        for (const item of payload[group] || []) {
          rows.push({
            label: item.name || item.profile || item.server,
            ok: item.ok,
            message: item.message,
          });
        }
      }
      renderList('providerHealth', rows, item => `
        <strong class="${item.ok ? 'health-ok' : 'health-bad'}">${item.ok ? 'OK' : 'FAIL'}</strong>
        <div>${item.label}</div>
        <div class="muted">${item.message}</div>
      `);
    }

    async function loadGrokNote() {
      const payload = await api('/api/v1/config/notes/grok-search');
      document.getElementById('modelNotes').textContent = pretty(payload);
    }

    async function loadClaudeNote() {
      const payload = await api('/api/v1/config/notes/claude-models');
      document.getElementById('modelNotes').textContent = pretty(payload);
    }

    loadSystemStatus();
    loadTemplates();
    loadTasks();
    loadConfig('search');
    loadConfig('llm');
    loadConfig('mcp');
    loadConfig('source-registry');
    loadCatalog();
  </script>
</body>
</html>
"""
