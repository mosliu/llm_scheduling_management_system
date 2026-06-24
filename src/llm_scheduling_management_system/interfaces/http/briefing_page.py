HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>信息研判助手</title>
  <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
  <style>
    :root {
      --bg: #f4f0e8;
      --bg-soft: #fbf7f0;
      --panel: rgba(255, 255, 255, 0.88);
      --ink: #1f2933;
      --muted: #607080;
      --line: rgba(31, 41, 51, 0.12);
      --line-strong: rgba(31, 41, 51, 0.2);
      --accent: #a94f2d;
      --accent-deep: #7f3518;
      --accent-soft: rgba(169, 79, 45, 0.1);
      --ok: #2b8a57;
      --warn: #d97706;
      --danger: #c2410c;
      --shadow: 0 24px 60px rgba(67, 49, 36, 0.12);
      --radius: 26px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "PingFang SC", "Microsoft YaHei UI", "Noto Sans SC", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(169,79,45,0.14), transparent 28%),
        radial-gradient(circle at top right, rgba(183, 146, 104, 0.16), transparent 22%),
        linear-gradient(180deg, var(--bg-soft) 0%, var(--bg) 100%);
    }
    [v-cloak] { display: none; }
    .page {
      max-width: 1240px;
      margin: 0 auto;
      padding: 32px 18px 52px;
    }
    .hero {
      display: grid;
      grid-template-columns: 1.35fr .65fr;
      gap: 18px;
      margin-bottom: 18px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 22px;
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
    }
    .panel.alt {
      background:
        linear-gradient(180deg, rgba(255,255,255,.94), rgba(251,247,240,.92));
    }
    h1, h2, h3, p {
      margin: 0;
    }
    h1 {
      font-size: 42px;
      line-height: 1.02;
      letter-spacing: -.03em;
      margin-bottom: 12px;
    }
    h2 {
      font-size: 26px;
      letter-spacing: -.02em;
      margin-bottom: 14px;
    }
    h3 {
      font-size: 17px;
      letter-spacing: -.01em;
      margin-bottom: 10px;
    }
    .lead {
      color: var(--muted);
      line-height: 1.7;
      max-width: 760px;
    }
    .badges, .actions, .meta-row, .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .badges {
      margin-top: 16px;
    }
    .badge {
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.78);
      color: var(--muted);
      font-size: 12px;
    }
    .meta-row {
      align-items: center;
      color: var(--muted);
      font-size: 13px;
      margin-top: 14px;
    }
    .layout {
      display: grid;
      grid-template-columns: 1fr;
      gap: 18px;
    }
    .input-grid {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 16px;
    }
    .span-12 { grid-column: span 12; }
    .span-8 { grid-column: span 8; }
    .span-6 { grid-column: span 6; }
    .span-4 { grid-column: span 4; }
    label {
      display: block;
      margin-bottom: 7px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: .01em;
    }
    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 13px 14px;
      color: var(--ink);
      background: rgba(255,255,255,.92);
      font: inherit;
      transition: border-color .18s ease, box-shadow .18s ease, background .18s ease;
    }
    textarea {
      min-height: 164px;
      line-height: 1.65;
      resize: vertical;
    }
    input:focus, textarea:focus {
      outline: none;
      border-color: rgba(169, 79, 45, 0.42);
      box-shadow: 0 0 0 4px rgba(169, 79, 45, 0.12);
      background: #fff;
    }
    .hint {
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
    }
    .chip-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 10px;
    }
    .check-card {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 13px 14px;
      background: rgba(255,255,255,.82);
      min-height: 78px;
    }
    .check-card input {
      width: 16px;
      height: 16px;
      margin-top: 3px;
      accent-color: var(--accent);
      flex: none;
    }
    .check-card strong {
      display: block;
      font-size: 14px;
      margin-bottom: 3px;
    }
    .check-card span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }
    button {
      border: 1px solid transparent;
      border-radius: 999px;
      padding: 11px 18px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      color: #fff;
      background: linear-gradient(180deg, var(--accent) 0%, var(--accent-deep) 100%);
      box-shadow: 0 12px 22px rgba(127, 53, 24, 0.22);
      transition: transform .18s ease, box-shadow .18s ease, opacity .18s ease;
    }
    button:hover { transform: translateY(-1px); }
    button.secondary {
      color: var(--ink);
      background: rgba(255,255,255,.9);
      border-color: var(--line);
      box-shadow: none;
    }
    button.ghost {
      color: var(--accent-deep);
      background: rgba(169,79,45,.06);
      border-color: rgba(169,79,45,.14);
      box-shadow: none;
    }
    button:disabled {
      opacity: .52;
      cursor: not-allowed;
      transform: none;
    }
    .message {
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 16px;
      font-size: 13px;
      line-height: 1.6;
      border: 1px solid transparent;
    }
    .message.info {
      color: #5c4536;
      background: rgba(169,79,45,.08);
      border-color: rgba(169,79,45,.14);
    }
    .message.error {
      color: #8a2f1c;
      background: rgba(194,65,12,.08);
      border-color: rgba(194,65,12,.18);
    }
    .status-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 16px;
    }
    .stat-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,.82);
    }
    .stat-label {
      color: var(--muted);
      font-size: 12px;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .stat-value {
      margin-top: 6px;
      font-size: 28px;
      font-weight: 800;
      letter-spacing: -.04em;
    }
    .progress-shell {
      margin-top: 16px;
      border-radius: 999px;
      overflow: hidden;
      background: rgba(96,112,128,.14);
      height: 14px;
    }
    .progress-fill {
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #cb6c39 0%, #8f391a 100%);
      transition: width .25s ease;
    }
    .split {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }
    .step-list, .timeline-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 520px;
      overflow: auto;
      padding-right: 4px;
    }
    .step-item, .timeline-item {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,.84);
    }
    .step-head, .timeline-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 6px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 11px;
      color: var(--muted);
      background: rgba(255,255,255,.9);
    }
    .tone-running { color: var(--warn); }
    .tone-succeeded { color: var(--ok); }
    .tone-failed { color: var(--danger); }
    .tone-queued { color: var(--muted); }
    .report-box {
      border: 1px solid var(--line);
      border-radius: 22px;
      background: rgba(255,255,255,.92);
      padding: 18px;
      white-space: pre-wrap;
      line-height: 1.82;
      font-size: 15px;
    }
    .report-empty {
      color: var(--muted);
      line-height: 1.7;
      padding: 16px 0 4px;
    }
    .mini-note {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
    }
    .limit-field {
      min-width: 180px;
    }
    .limit-field input {
      max-width: 180px;
    }
    .step-metrics {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px dashed var(--line);
      display: grid;
      gap: 7px;
    }
    .metric-title {
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }
    .metric-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .metric-row strong {
      color: var(--ink);
      text-align: right;
      overflow-wrap: anywhere;
    }
    .metric-empty {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    @media (max-width: 1100px) {
      .hero, .split, .status-grid { grid-template-columns: 1fr; }
      .span-8, .span-6, .span-4, .span-12 { grid-column: span 12; }
    }
    @media (max-width: 720px) {
      .page { padding: 16px 12px 36px; }
      h1 { font-size: 34px; }
      .panel { padding: 18px; border-radius: 22px; }
      .chip-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div id="app" class="page" v-cloak>
    <section class="hero">
      <div class="panel">
        <h1>信息研判助手</h1>
        <p class="lead">
          把你想了解的事情直接写进来，勾选需要用到的搜索源，系统会自动检索、整理，并持续回传进展，最后给出一份可直接阅读的结果。
        </p>
        <div class="badges">
          <span class="badge">独立于控制台</span>
          <span class="badge">面向非技术使用者</span>
          <span class="badge">可配置接口地址</span>
          <span class="badge">自动轮询进展</span>
        </div>
      </div>
      <div class="panel alt">
        <h3>使用说明</h3>
        <div class="meta-row">
          <span>1. 先确认 API 地址</span>
          <span>2. 输入你要查的内容</span>
          <span>3. 勾选搜索项</span>
          <span>4. 提交后等待结果</span>
        </div>
        <div class="meta-row">
          <span>如果部署地址是 `http://172.23.16.175:8000`，就在下方直接填写。</span>
        </div>
      </div>
    </section>

    <section class="layout">
      <div class="panel">
        <h2>提交任务</h2>
        <div class="input-grid">
          <div class="span-4">
            <label for="apiBase">接口地址</label>
            <input
              id="apiBase"
              v-model.trim="apiBaseInput"
              placeholder="默认使用当前页面所在地址，例如 http://172.23.16.175:8000"
              @change="saveApiBase"
            />
            <div class="hint">
              默认会走当前页面同一个地址。如果 API 跑在别的地方，可以改成完整地址，例如
              `http://172.23.16.175:8000`。
            </div>
          </div>
          <div class="span-4">
            <label for="apiPassword">访问密码</label>
            <input
              id="apiPassword"
              v-model.trim="apiPasswordInput"
              type="password"
              placeholder="可选，接口开启鉴权时填写"
              @change="saveApiPassword"
            />
            <div class="hint">
              如果 API 开启了 `X-LSMS-Password` 鉴权，就在这里填密码。
            </div>
          </div>
          <div class="span-4">
            <label for="taskLookupId">继续查看已有任务</label>
            <input
              id="taskLookupId"
              v-model.trim="taskLookupId"
              placeholder="输入任务 ID，例如 run_xxx"
              @keyup.enter="openExistingTask"
            />
            <div class="actions" style="margin-top:12px;">
              <button class="secondary" @click="resetApiBase">恢复同源</button>
              <button class="ghost" @click="openExistingTask" :disabled="!taskLookupId">打开任务</button>
            </div>
          </div>

          <div class="span-12">
            <label for="topic">你想让系统处理什么</label>
            <textarea
              id="topic"
              v-model="form.topic"
              placeholder="例如：请梳理某个事故、某个事件、某个热点话题的经过、关键时间线、官方回应、媒体报道和公众观点，并输出一份清晰的中文结果。"
            ></textarea>
            <div class="hint">可以直接写自然语言，不需要懂参数格式，也不需要懂工作流模板。</div>
          </div>

          <div class="span-12">
            <div class="toolbar" style="justify-content:space-between;align-items:flex-end;margin-bottom:10px;">
              <div>
                <label>勾选搜索项</label>
                <div class="mini-note">至少选择一个。默认会读取当前系统里已启用的搜索提供方。</div>
              </div>
              <div class="toolbar" style="align-items:flex-end;">
                <div class="limit-field">
                  <label for="searchLimit">搜索数量</label>
                  <input
                    id="searchLimit"
                    v-model.number="form.search_limit"
                    type="number"
                    min="1"
                    step="1"
                  />
                  <div class="mini-note">默认 20，每渠道</div>
                </div>
                <button class="secondary" @click="loadProviders" :disabled="loadingProviders">
                  {{ loadingProviders ? '读取中...' : '刷新搜索项' }}
                </button>
              </div>
            </div>
            <div class="chip-grid">
              <label class="check-card" v-for="provider in searchProviders" :key="provider.name">
                <input type="checkbox" :value="provider.name" v-model="form.search_provider_names" />
                <div>
                  <strong>{{ provider.display_name }}</strong>
                  <span>{{ provider.vendor_label }}</span>
                  <span>{{ provider.enabled ? '已启用' : '未启用' }}</span>
                </div>
              </label>
            </div>
          </div>

          <div class="span-12">
            <label class="check-card">
              <input type="checkbox" v-model="form.keep_china_sources_only" />
              <div>
                <strong>只保留中国来源</strong>
                <span>开启后，检索和合并结果只保留标记为中国来源的内容，海外或未知来源不会进入后续报告。</span>
              </div>
            </label>
          </div>
        </div>

        <div class="actions" style="margin-top:18px;">
          <button @click="submitTask" :disabled="submitting || !canSubmit">
            {{ submitting ? '提交中...' : '开始检索并整理' }}
          </button>
          <button class="secondary" @click="refreshTask" :disabled="!taskId || refreshing">
            {{ refreshing ? '刷新中...' : '立即刷新进展' }}
          </button>
          <button class="ghost" @click="clearCurrentTask" :disabled="!taskId">清空当前任务</button>
        </div>

        <div v-if="infoMessage" class="message info">{{ infoMessage }}</div>
        <div v-if="errorMessage" class="message error">{{ errorMessage }}</div>
      </div>

      <div class="panel" v-if="task">
        <div class="toolbar" style="justify-content:space-between;align-items:flex-start;">
          <div>
            <h2>进展状态</h2>
            <div class="meta-row">
              <span>任务 ID：{{ task.task_id }}</span>
              <span>状态：{{ statusLabel(task.status) }}</span>
              <span v-if="task.current_step">当前步骤：{{ humanizeStep(task.current_step) }}</span>
            </div>
          </div>
          <div class="pill" :class="statusToneClass(task.status)">
            {{ polling ? '轮询中' : '已停止轮询' }}
          </div>
        </div>

        <div class="progress-shell">
          <div class="progress-fill" :style="{ width: progressWidth }"></div>
        </div>

        <div class="status-grid">
          <div class="stat-card">
            <div class="stat-label">完成进度</div>
            <div class="stat-value">{{ task.progress.toFixed(0) }}%</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">已完成步骤</div>
            <div class="stat-value">{{ task.completed_step_count }}/{{ task.planned_step_count }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">最后刷新</div>
            <div class="stat-value" style="font-size:20px;">{{ lastUpdatedText || '尚未刷新' }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">任务模板</div>
            <div class="stat-value" style="font-size:18px;">{{ task.template_id }}</div>
          </div>
        </div>
      </div>

      <div class="split" v-if="task">
        <div class="panel">
          <h2>步骤进展</h2>
          <div class="step-list">
            <div class="step-item" v-for="step in task.steps" :key="step.step_run_id">
              <div class="step-head">
                <strong>{{ humanizeStep(step.node_key) }}</strong>
                <span class="pill" :class="statusToneClass(step.status)">{{ statusLabel(step.status) }}</span>
              </div>
              <div class="mini-note">内部标识：{{ step.node_key }}</div>
              <div class="mini-note">进度 {{ step.progress.toFixed(0) }}% · 缓存 {{ step.cache_hit ? '命中' : '未命中' }}</div>
              <div class="mini-note" v-if="step.error_message">异常：{{ step.error_message }}</div>
              <div class="step-metrics" v-if="shouldShowSearchMetrics(step)">
                <div class="metric-title">搜索结果统计</div>
                <div class="metric-row">
                  <span>每渠道上限</span>
                  <strong>{{ taskSearchLimit }} 条</strong>
                </div>
                <div class="metric-row" v-for="item in searchProviderSummaries" :key="item.name">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.count }} 条</strong>
                </div>
                <div class="metric-empty" v-if="!searchProviderSummaries.length">
                  尚未读取到搜索调用记录。
                </div>
                <div class="metric-empty" v-if="metricsError">{{ metricsError }}</div>
              </div>
              <div class="step-metrics" v-if="shouldShowFetchMetrics(step)">
                <div class="metric-title">正文抓取统计</div>
                <div class="metric-row">
                  <span>抓取方式</span>
                  <strong>{{ fetchMethodText }}</strong>
                </div>
                <div class="metric-row">
                  <span>抓取调用</span>
                  <strong>{{ fetchInvocationCount }} 次</strong>
                </div>
                <div class="metric-row">
                  <span>正文入库</span>
                  <strong>{{ fetchedDocumentCount }} 篇</strong>
                </div>
                <div class="metric-empty" v-if="metricsError">{{ metricsError }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="panel">
          <h2>结果输出</h2>
          <div class="status-grid" v-if="report && report.ready">
            <div class="stat-card">
              <div class="stat-label">时间线</div>
              <div class="stat-value">{{ report.timeline_count }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">官方回应</div>
              <div class="stat-value">{{ report.official_response_count }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">媒体观点</div>
              <div class="stat-value">{{ report.media_viewpoint_count }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">公众观点</div>
              <div class="stat-value">{{ report.public_viewpoint_count }}</div>
            </div>
          </div>

          <div v-if="report && report.ready" class="report-box">{{ report.report_text }}</div>
          <div v-else class="report-empty">
            <div>结果还没准备好时，这里会持续显示最新状态。</div>
            <div style="margin-top:8px;">如果任务长时间停留在“排队中”，通常意味着后端 worker 还没有启动，或者接口地址填错了。</div>
            <div v-if="report && report.message" style="margin-top:8px;">系统提示：{{ report.message }}</div>
          </div>
        </div>
      </div>
    </section>
  </div>

  <script>
    const SAME_ORIGIN_PROTOCOLS = new Set(['http:', 'https:']);
    const DEFAULT_API_BASE = SAME_ORIGIN_PROTOCOLS.has(window.location.protocol)
      && window.location.origin
      && window.location.origin !== 'null'
      ? window.location.origin.replace(/\/+$/, '')
      : '';
    const STORAGE_KEYS = {
      apiBase: 'briefing.apiBase',
      apiPassword: 'briefing.apiPassword',
      taskId: 'briefing.taskId',
    };
    const DEFAULT_SEARCH_LIMIT = 20;
    const ACTIVE_STATUSES = new Set(['queued', 'running', 'waiting_retry']);
    const COMPLETED_STEP_STATUSES = new Set(['succeeded', 'cached', 'partial_failed', 'failed', 'skipped']);
    const PROVIDER_LABELS = {
      exa_search: 'Exa 搜索',
      tavily_search: 'Tavily 搜索',
      grok_search: 'Grok 搜索',
      gpt_search: 'GPT 搜索',
      firecrawl_search: 'Firecrawl 搜索',
      tinyfish_search: 'Tinyfish 搜索',
    };
    const FETCH_PROVIDER_LABELS = {
      exa_contents: 'Exa Contents',
      firecrawl_scrape: 'Firecrawl Scrape',
      tavily_extract: 'Tavily Extract',
      tinyfish_fetch: 'Tinyfish Fetch',
    };
    const STEP_LABELS = {
      request_intake: '接收需求',
      search_fanout: '并行搜索',
      fetch_documents: '抓取正文',
      merge_search_results: '合并结果',
      normalize_and_filter: '清洗筛选',
      extract_event_time: '抽取时间',
      build_timeline: '整理时间线',
      extract_official_responses: '提取官方回应',
      segment_public_opinion: '拆分媒体与公众观点',
      generate_public_opinion_report: '生成最终报告',
      generate_event_summary: '生成事件摘要',
      analyze_public_opinion: '生成舆情分析',
      classify_and_filter_sources: '来源分类',
      mcp_lookup_context: '补充上下文',
      generate_timeline_report: '生成时间线报告',
    };
    const STATUS_LABELS = {
      queued: '排队中',
      running: '执行中',
      waiting_retry: '等待重试',
      succeeded: '已完成',
      failed: '失败',
      partial_failed: '部分失败',
      cancelled: '已取消',
      cached: '命中缓存',
      pending: '待执行',
      skipped: '已跳过',
    };
    const FALLBACK_PROVIDERS = [
      { name: 'exa_search', vendor: 'exa', enabled: true },
      { name: 'tavily_search', vendor: 'tavily', enabled: true },
      { name: 'grok_search', vendor: 'grok', enabled: true },
      { name: 'gpt_search', vendor: 'openai', enabled: true },
    ];

    const { createApp } = Vue;

    createApp({
      data() {
        const storedTaskId = localStorage.getItem(STORAGE_KEYS.taskId) || '';
        const storedApiBase = localStorage.getItem(STORAGE_KEYS.apiBase);
        const storedApiPassword = localStorage.getItem(STORAGE_KEYS.apiPassword) || '';
        const initialApiBase = storedApiBase || DEFAULT_API_BASE;
        return {
          apiBaseInput: initialApiBase,
          savedApiBase: initialApiBase,
          apiPasswordInput: storedApiPassword,
          loadingProviders: false,
          submitting: false,
          refreshing: false,
          polling: false,
          pollTimer: null,
          infoMessage: '',
          errorMessage: '',
          taskLookupId: storedTaskId,
          taskId: storedTaskId,
          task: null,
          report: null,
          taskMetrics: {
            searchInvocations: [],
            fetchInvocations: [],
            stats: null,
          },
          metricsError: '',
          lastUpdatedText: '',
          form: {
            topic: '',
            search_limit: DEFAULT_SEARCH_LIMIT,
            search_provider_names: [],
            keep_china_sources_only: false,
          },
          searchProviders: [],
        };
      },
      computed: {
        canSubmit() {
          return (
            this.form.topic.trim().length > 0
            && this.form.search_provider_names.length > 0
            && this.normalizedSearchLimit() > 0
          );
        },
        progressWidth() {
          if (!this.task) {
            return '0%';
          }
          const value = Number(this.task.progress || 0);
          return `${Math.max(0, Math.min(100, value))}%`;
        },
        taskSearchLimit() {
          return Number(this.task?.options_payload?.search_limit || this.form.search_limit || DEFAULT_SEARCH_LIMIT);
        },
        searchProviderSummaries() {
          const summaries = new Map();
          for (const invocation of this.taskMetrics.searchInvocations || []) {
            const name = invocation.provider_name || 'unknown_search';
            const existing = summaries.get(name) || {
              name,
              vendor: invocation.provider_vendor || '',
              count: 0,
            };
            existing.count += Number(invocation.result_count || 0);
            summaries.set(name, existing);
          }
          return Array.from(summaries.values()).map(item => ({
            ...item,
            label: this.providerDisplayName(item.name, item.vendor),
          }));
        },
        fetchProviderSummaries() {
          const summaries = new Map();
          for (const invocation of this.taskMetrics.fetchInvocations || []) {
            const name = invocation.provider_name || 'unknown_fetch';
            const existing = summaries.get(name) || {
              name,
              vendor: invocation.provider_vendor || '',
              calls: 0,
            };
            existing.calls += 1;
            summaries.set(name, existing);
          }
          return Array.from(summaries.values()).map(item => ({
            ...item,
            label: this.providerDisplayName(item.name, item.vendor),
          }));
        },
        fetchMethodText() {
          if (this.fetchProviderSummaries.length) {
            return this.fetchProviderSummaries
              .map(item => item.calls > 1 ? `${item.label} × ${item.calls}` : item.label)
              .join('、');
          }
          const configured = this.task?.options_payload?.fetch_provider_name;
          return configured ? this.providerDisplayName(configured) : '尚未记录';
        },
        fetchInvocationCount() {
          return (this.taskMetrics.fetchInvocations || []).length;
        },
        fetchedDocumentCount() {
          return Number(this.taskMetrics.stats?.document_count || 0);
        },
      },
      methods: {
        normalizedSearchLimit() {
          const value = Number(this.form.search_limit || DEFAULT_SEARCH_LIMIT);
          if (!Number.isFinite(value) || value < 1) {
            return 0;
          }
          return Math.floor(value);
        },
        normalizedApiBase(rawValue) {
          const value = (rawValue || '').trim();
          return value.replace(/\/+$/, '');
        },
        validateApiBase(rawValue) {
          const normalized = this.normalizedApiBase(rawValue);
          if (!normalized) {
            if (DEFAULT_API_BASE) {
              return { ok: true, value: DEFAULT_API_BASE };
            }
            return {
              ok: false,
              message: '当前页面是本地文件，请填写完整接口地址，例如 http://172.23.16.175:8000',
            };
          }
          let parsed;
          try {
            parsed = new URL(normalized);
          } catch (error) {
            return {
              ok: false,
              message: '接口地址格式不对，请填写完整地址，例如 http://172.23.16.175:8000',
            };
          }
          if (!['http:', 'https:'].includes(parsed.protocol)) {
            return {
              ok: false,
              message: '接口地址只能使用 http 或 https 协议。',
            };
          }
          return { ok: true, value: parsed.origin };
        },
        currentApiBase() {
          const result = this.validateApiBase(this.apiBaseInput);
          return result.ok ? result.value : '';
        },
        buildApiUrl(path) {
          const result = this.validateApiBase(this.apiBaseInput);
          if (!result.ok) {
            throw new Error(result.message);
          }
          return `${result.value}${path}`;
        },
        saveApiBase() {
          const result = this.validateApiBase(this.apiBaseInput);
          if (!result.ok) {
            this.errorMessage = result.message;
            this.infoMessage = '';
            return;
          }
          this.apiBaseInput = result.value;
          this.savedApiBase = result.value;
          localStorage.setItem(STORAGE_KEYS.apiBase, result.value);
          this.infoMessage = `接口地址已设置为 ${result.value}`;
          this.errorMessage = '';
          this.loadProviders();
        },
        resetApiBase() {
          if (!DEFAULT_API_BASE) {
            this.apiBaseInput = '';
            this.savedApiBase = '';
            localStorage.removeItem(STORAGE_KEYS.apiBase);
            this.infoMessage = '当前页面不是 http(s) 页面，无法恢复同源，请手动填写完整接口地址。';
            this.errorMessage = '';
            return;
          }
          this.apiBaseInput = DEFAULT_API_BASE;
          const result = this.validateApiBase(this.apiBaseInput);
          if (result.ok) {
            this.savedApiBase = result.value;
            localStorage.setItem(STORAGE_KEYS.apiBase, result.value);
            this.infoMessage = `接口地址已设置为 ${result.value}`;
            this.errorMessage = '';
            this.loadProviders();
            return;
          }
          this.savedApiBase = '';
          localStorage.removeItem(STORAGE_KEYS.apiBase);
          this.infoMessage = '';
          this.errorMessage = result.message;
        },
        saveApiPassword() {
          this.apiPasswordInput = (this.apiPasswordInput || '').trim();
          localStorage.setItem(STORAGE_KEYS.apiPassword, this.apiPasswordInput);
          this.infoMessage = this.apiPasswordInput
            ? '访问密码已保存到当前浏览器。'
            : '访问密码已清空。';
          this.errorMessage = '';
        },
        statusLabel(status) {
          return STATUS_LABELS[status] || status || '未知状态';
        },
        statusToneClass(status) {
          if (status === 'succeeded') {
            return 'tone-succeeded';
          }
          if (status === 'failed' || status === 'partial_failed' || status === 'cancelled') {
            return 'tone-failed';
          }
          if (status === 'running' || status === 'waiting_retry') {
            return 'tone-running';
          }
          return 'tone-queued';
        },
        humanizeStep(stepKey) {
          return STEP_LABELS[stepKey] || stepKey || '未命名步骤';
        },
        providerDisplayName(name, vendor = '') {
          const label = PROVIDER_LABELS[name] || FETCH_PROVIDER_LABELS[name] || name || '未知渠道';
          if (!vendor || vendor === 'unknown') {
            return label;
          }
          return `${label}（${vendor}）`;
        },
        formatProvider(provider) {
          const displayName = this.providerDisplayName(provider.name);
          const vendorLabel = provider.vendor ? `来源：${provider.vendor}` : '来源未标注';
          return {
            ...provider,
            display_name: displayName,
            vendor_label: vendorLabel,
          };
        },
        buildRequestHeaders(extraHeaders = {}) {
          const headers = { ...extraHeaders };
          if (this.apiPasswordInput) {
            headers['X-LSMS-Password'] = this.apiPasswordInput;
          }
          return headers;
        },
        async request(path, options = {}) {
          const response = await fetch(this.buildApiUrl(path), {
            ...options,
            headers: this.buildRequestHeaders(options.headers || {}),
          });
          const contentType = response.headers.get('content-type') || '';
          const payload = contentType.includes('application/json')
            ? await response.json()
            : await response.text();
          if (!response.ok) {
            const detail = payload && payload.detail;
            const message = detail && typeof detail === 'object'
              ? detail.message || detail.code || JSON.stringify(detail)
              : detail || payload || `请求失败：${response.status}`;
            throw new Error(message);
          }
          return payload;
        },
        resetTaskMetrics() {
          this.taskMetrics = {
            searchInvocations: [],
            fetchInvocations: [],
            stats: null,
          };
          this.metricsError = '';
        },
        isStepCompleted(step) {
          return step && COMPLETED_STEP_STATUSES.has(step.status);
        },
        shouldShowSearchMetrics(step) {
          return step.node_key === 'search_fanout' && this.isStepCompleted(step);
        },
        shouldShowFetchMetrics(step) {
          return step.node_key === 'fetch_documents' && this.isStepCompleted(step);
        },
        async refreshTaskMetrics() {
          if (!this.taskId) {
            this.resetTaskMetrics();
            return;
          }
          const [searchResult, fetchResult, statsResult] = await Promise.allSettled([
            this.request(`/api/v1/tasks/${this.taskId}/search-invocations`),
            this.request(`/api/v1/tasks/${this.taskId}/fetch-invocations`),
            this.request(`/api/v1/tasks/${this.taskId}/stats`),
          ]);
          if (searchResult.status === 'fulfilled') {
            this.taskMetrics.searchInvocations = Array.isArray(searchResult.value) ? searchResult.value : [];
          }
          if (fetchResult.status === 'fulfilled') {
            this.taskMetrics.fetchInvocations = Array.isArray(fetchResult.value) ? fetchResult.value : [];
          }
          if (statsResult.status === 'fulfilled') {
            this.taskMetrics.stats = statsResult.value || null;
          }
          const failed = [searchResult, fetchResult, statsResult]
            .filter(item => item.status === 'rejected')
            .map(item => item.reason?.message || '未知错误');
          this.metricsError = failed.length ? `统计读取失败：${failed.join('；')}` : '';
        },
        async loadProviders() {
          this.loadingProviders = true;
          try {
            const providers = await this.request('/api/v1/provider-catalog/search');
            const enabledProviders = (providers || []).filter(item => item.enabled !== false);
            const source = enabledProviders.length ? enabledProviders : providers;
            this.searchProviders = (source || []).map(this.formatProvider);
            if (!this.searchProviders.length) {
              this.searchProviders = FALLBACK_PROVIDERS.map(this.formatProvider);
            }
            if (!this.form.search_provider_names.length) {
              this.form.search_provider_names = this.searchProviders
                .filter(item => item.enabled !== false)
                .map(item => item.name);
            } else {
              const available = new Set(this.searchProviders.map(item => item.name));
              this.form.search_provider_names = this.form.search_provider_names.filter(name => available.has(name));
              if (!this.form.search_provider_names.length) {
                this.form.search_provider_names = this.searchProviders.map(item => item.name);
              }
            }
            this.errorMessage = '';
          } catch (error) {
            this.searchProviders = FALLBACK_PROVIDERS.map(this.formatProvider);
            if (!this.form.search_provider_names.length) {
              this.form.search_provider_names = this.searchProviders.map(item => item.name);
            }
            this.errorMessage = `搜索项读取失败：${error.message}`;
          } finally {
            this.loadingProviders = false;
          }
        },
        async submitTask() {
          if (!this.form.topic.trim()) {
            this.errorMessage = '请先输入你想让系统处理的内容。';
            return;
          }
          if (!this.form.search_provider_names.length) {
            this.errorMessage = '请至少勾选一个搜索项。';
            return;
          }
          const searchLimit = this.normalizedSearchLimit();
          if (!searchLimit) {
            this.errorMessage = '搜索数量必须是大于 0 的整数。';
            return;
          }
          this.form.search_limit = searchLimit;
          this.submitting = true;
          this.errorMessage = '';
          this.infoMessage = '';
          this.report = null;
          this.resetTaskMetrics();
          try {
            const payload = {
              topic: this.form.topic.trim(),
              search_provider_names: [...this.form.search_provider_names],
              search_limit: searchLimit,
              keep_china_sources_only: this.form.keep_china_sources_only,
              execution_engine: 'native',
              auto_start: true,
            };
            const result = await this.request('/api/v1/reports/public-opinion', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload),
            });
            this.taskId = result.task_id;
            this.taskLookupId = result.task_id;
            localStorage.setItem(STORAGE_KEYS.taskId, result.task_id);
            this.infoMessage = `任务 ${result.task_id} 已提交，系统正在后台处理。`;
            await this.refreshTask();
            this.startPolling();
          } catch (error) {
            this.errorMessage = `提交失败：${error.message}`;
          } finally {
            this.submitting = false;
          }
        },
        async openExistingTask() {
          if (!this.taskLookupId.trim()) {
            return;
          }
          this.taskId = this.taskLookupId.trim();
          localStorage.setItem(STORAGE_KEYS.taskId, this.taskId);
          this.report = null;
          this.resetTaskMetrics();
          await this.refreshTask();
          if (this.task && ACTIVE_STATUSES.has(this.task.status)) {
            this.startPolling();
          }
        },
        async loadFinalReport() {
          if (!this.taskId) {
            return;
          }
          try {
            this.report = await this.request(`/api/v1/reports/public-opinion/${this.taskId}/final-report`);
          } catch (error) {
            this.report = {
              ready: false,
              message: error.message,
            };
          }
        },
        async refreshTask() {
          if (!this.taskId) {
            return;
          }
          this.refreshing = true;
          try {
            this.task = await this.request(`/api/v1/tasks/${this.taskId}`);
            await this.refreshTaskMetrics();
            this.lastUpdatedText = new Date().toLocaleString('zh-CN');
            if (ACTIVE_STATUSES.has(this.task.status)) {
              this.infoMessage = `任务正在执行：${this.statusLabel(this.task.status)}。页面会自动继续刷新。`;
              this.startPolling();
            } else {
              this.stopPolling();
              if (this.task.status === 'succeeded') {
                this.infoMessage = '任务已完成，正在加载最终结果。';
              } else {
                this.infoMessage = `任务状态：${this.statusLabel(this.task.status)}。`;
              }
            }
            if (this.task.status === 'succeeded' || !ACTIVE_STATUSES.has(this.task.status)) {
              await this.loadFinalReport();
            }
            this.errorMessage = '';
          } catch (error) {
            this.errorMessage = `进展读取失败：${error.message}`;
            this.stopPolling();
          } finally {
            this.refreshing = false;
          }
        },
        startPolling() {
          if (this.pollTimer || !this.taskId) {
            this.polling = Boolean(this.pollTimer);
            return;
          }
          this.polling = true;
          this.pollTimer = window.setInterval(() => {
            this.refreshTask();
          }, 2500);
        },
        stopPolling() {
          if (this.pollTimer) {
            window.clearInterval(this.pollTimer);
            this.pollTimer = null;
          }
          this.polling = false;
        },
        clearCurrentTask() {
          this.stopPolling();
          this.taskId = '';
          this.taskLookupId = '';
          this.task = null;
          this.report = null;
          this.resetTaskMetrics();
          this.lastUpdatedText = '';
          localStorage.removeItem(STORAGE_KEYS.taskId);
          this.infoMessage = '当前任务已清空。';
          this.errorMessage = '';
        },
      },
      async mounted() {
        const result = this.validateApiBase(this.apiBaseInput);
        if (result.ok) {
          this.apiBaseInput = result.value;
          this.savedApiBase = result.value;
          localStorage.setItem(STORAGE_KEYS.apiBase, result.value);
          await this.loadProviders();
        } else {
          this.savedApiBase = '';
          localStorage.removeItem(STORAGE_KEYS.apiBase);
          this.errorMessage = result.message;
        }
        if (this.taskId) {
          await this.refreshTask();
        }
      },
      beforeUnmount() {
        this.stopPolling();
      },
    }).mount('#app');
  </script>
</body>
</html>
"""
