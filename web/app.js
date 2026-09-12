// 常數定義
const stages = {
  'S1': { name: '接收與分類檔案', fatal: false },
  'S2': { name: '解析各分頁', fatal: false },
  'S3': { name: '一致性稽核', fatal: false },
  'S4': { name: '取得投手左右手', fatal: false },
  'S5': { name: '姓名比對', fatal: false },
  'S6': { name: '聚合統計', fatal: false },
  'S7': { name: '交叉驗證', fatal: false },
  'S8': { name: '產出 HTML', fatal: true }
}
const stageOrder = Object.keys(stages)
const picked = []

// 功能函數定義
const el = (id) => document.getElementById(id)

const esc = (text) => String(text === null || text === undefined ? '' : text)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

// 進度條格子：一個階段一格
const renderStages = () => {
  el('stages').innerHTML = stageOrder.map((id) =>
    `<div class="stage" id="stage-${id}" data-state="idle"><b>${id}</b>${stages[id].name}</div>`).join('')
}

// 更新單一格子的狀態
const setStage = (id, state) => {
  const box = el(`stage-${id}`)
  if (box) box.dataset.state = state
}

// 進度條寬度依已完成的階段數推進
const setBar = (doneCount) => {
  el('bar').style.width = `${Math.round(doneCount / stageOrder.length * 100)}%`
}

// 選檔後列出檔名
const renderFiles = () => {
  el('files').innerHTML = picked.map((file) =>
    `<li>${esc(file.name)}（${Math.round(file.size / 1024)} KB）</li>`).join('')
  el('run').disabled = picked.length === 0
}

// 收檔：拖曳與挑選共用
const addFiles = (fileList) => {
  Array.from(fileList).forEach((file) => picked.push(file))
  renderFiles()
}

// 寫一行日誌，錯誤與警告上色，方便整段複製
const appendLog = (event) => {
  const line = `[${event.ts}] ${event.stage} ${event.level.toUpperCase()} ${event.msg}` +
    (event.detail ? ` ${JSON.stringify(event.detail)}` : '')
  const row = document.createElement('div')
  row.className = event.level
  row.textContent = line
  el('log').appendChild(row)
  el('log').scrollTop = el('log').scrollHeight
}

// 收到 done 事件時的總結：只有 S8 失敗才算整體失敗
const showResult = (summary) => {
  const box = el('result')
  box.hidden = false
  box.className = `result ${summary.ok ? 'ok' : 'bad'}`
  const link = summary.output
    ? ` <a href="/out/${encodeURIComponent(summary.output)}" target="_blank">開啟產出的對照表</a>`
    : ''
  const failed = (summary.stages || []).filter((stage) => !stage.ok).map((stage) => stage.id)
  const note = failed.length ? `降級處理的階段：${failed.join('、')}。` : '八個階段全部成功。'
  box.innerHTML = `${summary.ok ? '處理完成。' : '處理失敗（S8 未產出）。'} ${note}${link}`
}

// 逐筆消化 SSE 事件
const handleEvent = (event, state) => {
  if (event.type === 'done') {
    (event.stages || []).forEach((stage) => setStage(stage.id, stage.ok ? 'ok' : 'failed'))
    setBar(stageOrder.length)
    showResult(event)
    return true
  }
  appendLog(event)
  if (event.msg && event.msg.endsWith('開始')) setStage(event.stage, 'running')
  if (event.msg && event.msg.indexOf('成功 耗時') >= 0) {
    setStage(event.stage, 'ok')
    state.done += 1
    setBar(state.done)
  }
  if (event.level === 'error' && event.msg.indexOf('失敗 耗時') >= 0) {
    setStage(event.stage, 'failed')
    state.done += 1
    setBar(state.done)
  }
  return false
}

// 訂閱進度：SSE 單向即可，不用 WebSocket
const subscribe = (runId) => {
  const state = { done: 0 }
  const source = new EventSource(`/api/progress?run=${runId}`)
  source.onmessage = (message) => {
    const event = JSON.parse(message.data)
    if (handleEvent(event, state)) source.close()
  }
  source.onerror = () => { source.close() }
}

// 上傳並啟動一次執行
const start = async () => {
  el('run').disabled = true
  el('log').innerHTML = ''
  el('result').hidden = true
  renderStages()
  setBar(0)
  const form = new FormData()
  picked.forEach((file) => form.append('files', file, file.name))
  const response = await fetch('/api/upload', { method: 'POST', body: form })
  const payload = await response.json()
  if (payload.error) {
    appendLog({ ts: new Date().toISOString(), stage: 'S1', level: 'error', msg: payload.error })
    el('run').disabled = false
    return
  }
  subscribe(payload.run)
}

// 綁定畫面事件
const bind = () => {
  el('choose').addEventListener('click', () => el('picker').click())
  el('picker').addEventListener('change', (event) => addFiles(event.target.files))
  el('run').addEventListener('click', start)
  el('copy').addEventListener('click', () => navigator.clipboard.writeText(el('log').textContent))
  const drop = el('drop')
  drop.addEventListener('dragover', (event) => { event.preventDefault(); drop.classList.add('over') })
  drop.addEventListener('dragleave', () => drop.classList.remove('over'))
  drop.addEventListener('drop', (event) => {
    event.preventDefault()
    drop.classList.remove('over')
    addFiles(event.dataTransfer.files)
  })
}

renderStages()
bind()
