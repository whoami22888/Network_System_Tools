const installButton = document.querySelector('#installButton');
const apiInput = document.querySelector('#apiBase');
const bridgeInput = document.querySelector('#agentBridge');
let deferredInstallPrompt;
const screenLog = [];

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js'));
}

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  installButton.hidden = false;
});

installButton.addEventListener('click', async () => {
  if (!deferredInstallPrompt) return;
  deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = undefined;
  installButton.hidden = true;
});

apiInput.value = localStorage.getItem('nst.apiBase') || '';
bridgeInput.value = localStorage.getItem('nst.bridgeUrl') || bridgeInput.value;
loadFeaturePolicy();

document.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-tool]');
  if (!button) return;

  if (button.dataset.tool === 'connectivity') await runConnectivityCheck();
  if (button.dataset.tool === 'agent') saveAgentEndpoint();
  if (button.dataset.tool === 'device') showDeviceContext();
  if (button.dataset.tool === 'chat') await sendChat();
  if (button.dataset.tool === 'terminal') await runTerminalCommand();
  if (button.dataset.tool === 'listTools') await listTools();
  if (button.dataset.tool === 'uploadSkill') await uploadSkill();
  if (button.dataset.tool === 'downloadLog') downloadScreenLog();
});

async function runConnectivityCheck() {
  const output = document.querySelector('#connectivityOutput');
  output.value = 'Checking browser connectivity...';
  const started = performance.now();
  try {
    await fetch('https://example.com/', { mode: 'no-cors', cache: 'no-store' });
    output.value = `Reachable. Browser request completed in ${Math.round(performance.now() - started)} ms.`;
    recordAction('connectivity', output.value);
  } catch (error) {
    output.value = `Unable to complete browser request: ${error.message}`;
    recordAction('connectivity_error', output.value);
  }
}

function saveAgentEndpoint() {
  const output = document.querySelector('#agentOutput');
  const value = apiInput.value.trim().replace(/\/$/, '');
  if (!value) {
    localStorage.removeItem('nst.apiBase');
    output.value = 'Endpoint cleared. Add your cloud API when it is available.';
    return;
  }
  localStorage.setItem('nst.apiBase', value);
  output.value = `Cloud endpoint saved: ${value}\nNext step: implement /health and approved diagnostic routes server-side.`;
  recordAction('cloud_endpoint_saved', value);
}

function showDeviceContext() {
  const output = document.querySelector('#deviceOutput');
  output.value = [
    `Online: ${navigator.onLine ? 'yes' : 'no'}`,
    `Platform: ${navigator.platform || 'unknown'}`,
    `User agent: ${navigator.userAgent}`,
    `Viewport: ${window.innerWidth} x ${window.innerHeight}`,
    `Standalone display: ${matchMedia('(display-mode: standalone)').matches ? 'yes' : 'no'}`,
  ].join('\n');
  recordAction('device_context', output.value);
}

async function loadFeaturePolicy() {
  const output = document.querySelector('#agentOutput');
  try {
    const response = await fetch('/config/features.json', { cache: 'no-store' });
    const policy = await response.json();
    const enabled = Object.entries(policy.features || {})
      .filter(([, value]) => value)
      .map(([name]) => name)
      .join(', ');
    output.value = `All local app features are unlocked. Enabled: ${enabled}`;
    recordAction('feature_policy_loaded', policy);
  } catch (error) {
    output.value = `Feature policy unavailable; defaulting to unlocked local app features. ${error.message}`;
    recordAction('feature_policy_error', error.message);
  }
}

async function sendChat() {
  const output = document.querySelector('#chatOutput');
  const message = document.querySelector('#chatPrompt').value.trim();
  if (!message) {
    output.value = 'Enter a message for the assistant.';
    return;
  }
  output.value = 'Sending to local WhiteRabbitNeo/Ollama bridge...';
  try {
    const payload = await postBridge('/chat', { message });
    output.value = payload.answer || JSON.stringify(payload, null, 2);
    recordAction('ai_chat', { message, response: payload });
  } catch (error) {
    output.value = `Chat failed: ${error.message}`;
    recordAction('ai_chat_error', error.message);
  }
}

async function runTerminalCommand() {
  const output = document.querySelector('#terminalOutput');
  const command = document.querySelector('#terminalCommand').value.trim();
  const consent = document.querySelector('#consentToggle').checked;
  const internet_enabled = document.querySelector('#internetToggle').checked;
  if (!command) {
    output.value = 'Enter a command first.';
    return;
  }
  output.value = `Visible action request:\n${command}\nWaiting for local bridge...`;
  try {
    await postBridge('/settings', { internet_enabled, logging_enabled: true });
    const payload = await postBridge('/terminal', { command, consent });
    output.value = [`$ ${command}`, payload.stdout || '', payload.stderr || '', payload.error || ''].filter(Boolean).join('\n');
    recordAction('terminal', { command, internet_enabled, payload });
  } catch (error) {
    output.value = `Terminal action blocked or failed: ${error.message}`;
    recordAction('terminal_error', { command, error: error.message });
  }
}

async function listTools() {
  const output = document.querySelector('#skillsOutput');
  try {
    const response = await fetch(`${bridgeInput.value.trim().replace(/\/$/, '')}/tools`);
    const payload = await response.json();
    output.value = (payload.tools || [])
      .map((tool) => `${tool.name} [${tool.category || 'custom'}] - ${tool.description || tool.source}`)
      .join('\n') || 'No tools found.';
    recordAction('tool_list', payload);
  } catch (error) {
    output.value = `Tool list unavailable: ${error.message}`;
    recordAction('tool_list_error', error.message);
  }
}

async function uploadSkill() {
  const output = document.querySelector('#skillsOutput');
  const file = document.querySelector('#skillFile').files[0];
  if (!file) {
    output.value = 'Choose a JSON tool or skill file first.';
    return;
  }
  try {
    const content = JSON.parse(await file.text());
    const payload = await postBridge('/tools', { name: file.name, content });
    output.value = `Uploaded ${file.name} to ${payload.path}`;
    recordAction('skill_upload', payload);
  } catch (error) {
    output.value = `Upload failed: ${error.message}`;
    recordAction('skill_upload_error', error.message);
  }
}

function downloadScreenLog() {
  const blob = new Blob([JSON.stringify(screenLog, null, 2)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `network-system-tools-log-${new Date().toISOString()}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}

async function postBridge(path, payload) {
  const bridgeUrl = bridgeInput.value.trim().replace(/\/$/, '');
  localStorage.setItem('nst.bridgeUrl', bridgeUrl);
  const response = await fetch(`${bridgeUrl}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

function recordAction(kind, detail) {
  screenLog.push({ time: new Date().toISOString(), kind, detail });
}
