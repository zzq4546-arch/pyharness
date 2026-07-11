let ws;
let pendingApprovalId = null;

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${location.host}/ws`);
  ws.onmessage = (e) => {
    const event = JSON.parse(e.data);
    handleEvent(event);
  };
  ws.onclose = () => setTimeout(connect, 2000);
}

function handleEvent(event) {
  const out = document.getElementById('terminal-output');
  const div = document.createElement('div');
  switch (event.type) {
    case 'status':
      div.className = 'log-system';
      div.textContent = `[系统] ${event.status}: ${event.task || ''} (最大轮次: ${event.max_rounds || ''})`;
      document.getElementById('agent-status').textContent = event.status;
      document.getElementById('agent-round').textContent = `${event.round || 0}/${event.max_rounds || 0}`;
      break;
    case 'llm_response':
      div.className = 'log-agent';
      div.textContent = `[agent] ${event.content}`;
      break;
    case 'action':
      div.className = 'log-agent';
      div.textContent = `[agent] 动作: ${event.action_type} ${event.tool_name || ''}`;
      break;
    case 'guardrail':
      const gr = event.result;
      div.className = gr.blocked ? 'log-guard' : (gr.needs_approval ? 'log-approval' : 'log-system');
      if (gr.blocked) {
        div.textContent = `[护栏] 拦截: ${gr.reason} (${gr.guard_name})`;
        document.getElementById('guard-blocks').textContent = parseInt(document.getElementById('guard-blocks').textContent) + 1;
      } else if (gr.needs_approval) {
        div.textContent = `[护栏] 需要审批: ${gr.reason}`;
      }
      break;
    case 'approval_required':
      pendingApprovalId = event.approval_id;
      document.getElementById('approval-content').textContent =
        `操作: ${event.action.tool_name} ${JSON.stringify(event.action.tool_args)}`;
      document.getElementById('approval-box').classList.remove('hidden');
      div.className = 'log-approval';
      div.textContent = `[审批] 等待审批: ${event.action.tool_name}`;
      break;
    case 'approval_result':
      div.className = 'log-system';
      div.textContent = `[审批] 结果: ${event.decision}`;
      document.getElementById('approval-box').classList.add('hidden');
      pendingApprovalId = null;
      break;
    case 'executing':
      div.className = 'log-agent';
      div.textContent = `[agent] 执行: ${event.tool_name}`;
      break;
    case 'tool_result':
      div.className = event.success ? 'log-agent' : 'log-feedback';
      div.textContent = `[结果] ${event.success ? '成功' : '失败'}: ${event.output?.substring(0, 200) || ''}`;
      break;
    case 'feedback':
      div.className = event.status === 'PASS' ? 'log-agent' : 'log-feedback';
      div.textContent = `[反馈] ${event.status}: ${event.summary}`;
      break;
    case 'done':
      div.className = 'log-system';
      div.textContent = `[完成] ${JSON.stringify(event.result)}`;
      document.getElementById('agent-status').textContent = '空闲';
      break;
    case 'error':
      div.className = 'log-guard';
      div.textContent = `[错误] ${event.error}`;
      break;
    case 'round':
      document.getElementById('agent-round').textContent = `${event.round}/0`;
      break;
    default:
      div.className = 'log-system';
      div.textContent = JSON.stringify(event);
  }
  out.appendChild(div);
  out.scrollTop = out.scrollHeight;
}

function sendTask() {
  const input = document.getElementById('user-input');
  const task = input.value.trim();
  if (!task) return;
  const out = document.getElementById('terminal-output');
  const div = document.createElement('div');
  div.className = 'log-user';
  div.textContent = `$ ${task}`;
  out.appendChild(div);
  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task }),
  });
  input.value = '';
}

function handleApproval(decision) {
  if (!pendingApprovalId) return;
  fetch('/api/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approval_id: pendingApprovalId, decision }),
  });
  document.getElementById('approval-box').classList.add('hidden');
}

function stopAgent() {
  fetch('/api/stop', { method: 'POST' });
}

async function checkKeyStatus() {
  const resp = await fetch('/api/credential/status');
  const data = await resp.json();
  document.getElementById('key-status').textContent = data.configured ? '已配置' : '未配置';
  if (!data.configured) {
    document.getElementById('setup-modal').classList.remove('hidden');
  }
}

async function saveApiKey() {
  const key = document.getElementById('api-key-input').value.trim();
  if (!key) return;
  await fetch('/api/credential/set', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key }),
  });
  document.getElementById('setup-modal').classList.add('hidden');
  document.getElementById('key-status').textContent = '已配置';
}

function closeSetup() {
  document.getElementById('setup-modal').classList.add('hidden');
}

function showConfig() { alert('配置文件: .harness/config.yaml'); }
function showGuardLog() { alert('护栏日志查看（待实现）'); }

document.getElementById('user-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendTask();
});

connect();
checkKeyStatus();