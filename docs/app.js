//版本鎖死：換版要連同 sw.js 的快取版本與 CHECKLIST-B.md 的實機驗證一起重來
const PYODIDE_VERSION = 'v314.0.6'
const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/${PYODIDE_VERSION}/full/`
const PAYLOAD_URL = 'payload/pipeline.zip'
//管線在虛擬檔案系統裡的輸出位置，讀回來後轉成 Blob，不會離開這支手機
const OUTPUT_PATH = '/out/report.html'
const MB = 1024 * 1024

//瀏覽器端的膠水：把 JS 的檔案與回呼接到 web.pipeline，事件一律轉成 JSON 字串再交回 JS，
//免得 JS 端要處理 PyProxy 的生命週期
const GLUE = `
import json
from web import pipeline
from adapters.roster_cache import CachedRosterSource

def web_settings():
    return json.dumps(pipeline.load_config()['settings'])

def web_roster_dates():
    config = pipeline.load_config()
    codes = [meta['npb_code'] for meta in config['team_meta'].values()]
    return json.dumps(CachedRosterSource().fetched_dates(codes))

def web_run(entries, sink, output_path):
    files = [(entry[0], entry[1].to_bytes()) for entry in entries]
    log = pipeline.RunLog(sink=lambda event: sink(json.dumps(event, ensure_ascii=False)))
    result = pipeline.run_pipeline(files, CachedRosterSource(), pipeline.load_config(),
                                   log, output_path)
    return json.dumps({'ok': result['ok'], 'stages': result['stages'],
                       'skipped': result['skipped'], 'errors': result['errors'],
                       'player': result['player']},
                      ensure_ascii=False)
`

const state = { pyodide: null, picked: [], maxBytes: 20 * MB, reportUrl: null, player: '' }

const el = (id) => document.getElementById(id)

//所有例外都落到畫面上，log 保留不清，方便使用者整段截圖回報
const showError = (error) => {
  const box = el('error')
  box.textContent = `發生錯誤：${error && error.message ? error.message : error}`
  box.hidden = false
}

//寫一行 log；detail 一併印出，錯誤與警告從文字就看得出來
const appendLog = (event) => {
  const line = `[${event.ts}] ${event.stage} ${event.level.toUpperCase()} ${event.msg}` +
    (event.detail ? ` ${JSON.stringify(event.detail)}` : '')
  const log = el('log')
  log.textContent += `${line}\n`
  log.scrollTop = log.scrollHeight
}

const bootMsg = (text) => { el('boot-msg').textContent = text }

//pyodide.js 是傳統腳本、會掛出全域 loadPyodide，模組腳本裡只能用插入 <script> 的方式載入
const loadScript = (src) => new Promise((resolve, reject) => {
  const script = document.createElement('script')
  script.src = src
  script.onload = resolve
  script.onerror = () => reject(new Error(`無法載入 ${src}，請確認網路後重新整理`))
  document.head.appendChild(script)
})

//步驟 1–4：載入 Pyodide、內建的 beautifulsoup4、解開管線 zip，然後才讓使用者選檔
const boot = async () => {
  bootMsg('正在下載 Python 執行環境（第一次較久）…')
  await loadScript(`${PYODIDE_BASE}pyodide.js`)
  const pyodide = await window.loadPyodide({ indexURL: PYODIDE_BASE })
  //bs4 已內建於 Pyodide 發行版，不走 micropip，不連 PyPI
  bootMsg('正在載入 HTML 解析套件…')
  await pyodide.loadPackage('beautifulsoup4')
  bootMsg('正在解開處理程式…')
  const response = await fetch(PAYLOAD_URL)
  if (!response.ok) throw new Error(`讀不到 ${PAYLOAD_URL}（HTTP ${response.status}）`)
  pyodide.unpackArchive(await response.arrayBuffer(), 'zip')
  pyodide.runPython(GLUE)
  const settings = JSON.parse(pyodide.globals.get('web_settings')())
  state.maxBytes = (settings.max_upload_size_mb || 20) * MB
  state.pyodide = pyodide
  el('boot').hidden = true
  el('picker').hidden = false
}

//名冊是預先打包的快照，過期也只能用，所以把抓取日期攤給使用者自己判斷
const logRosterDates = () => {
  const dates = JSON.parse(state.pyodide.globals.get('web_roster_dates')())
  const known = Object.values(dates).filter(Boolean).sort()
  const missing = Object.keys(dates).filter((code) => !dates[code])
  const range = known.length ? `${known[0]} ～ ${known[known.length - 1]}` : '無'
  appendLog({ ts: new Date().toISOString().slice(0, 19), stage: 'S4', level: missing.length ? 'warn' : 'info',
    msg: `名冊快照抓取日期 ${range}，共 ${known.length} 隊` + (missing.length ? `，缺 ${missing.join('、')}` : '') })
}

//步驟 5：列出選到的檔案；超過大小上限的直接標出來、不送進管線
const renderFiles = () => {
  const list = el('filelist')
  list.textContent = ''
  state.picked.forEach((file) => {
    const item = document.createElement('li')
    const over = file.size > state.maxBytes
    item.textContent = `${file.name}（${Math.max(1, Math.round(file.size / 1024))} KB）` +
      (over ? `：超過 ${state.maxBytes / MB} MB，略過` : '')
    list.appendChild(item)
  })
  el('run').disabled = usableFiles().length === 0
}

const usableFiles = () => state.picked.filter((file) => file.size <= state.maxBytes)

//八階段進度：依 RunLog 的「開始／成功／失敗」訊息推進，與本機窗口的判讀方式一致
const updateProgress = (event) => {
  const index = Number(String(event.stage).replace('S', '')) - 1
  const item = el('progress').children[index]
  if (!item) return
  if (event.msg.endsWith('開始')) item.className = 'active'
  if (event.msg.includes('成功 耗時')) item.className = 'done'
  if (event.level === 'error' && event.msg.includes('失敗 耗時')) {
    item.className = 'done'
    item.dataset.failed = 'true'
    item.textContent = `${item.textContent.replace(/（失敗）$/, '')}（失敗）`
  }
}

const resetProgress = () => {
  Array.from(el('progress').children).forEach((item) => {
    item.className = ''
    item.textContent = item.textContent.replace(/（失敗）$/, '')
    delete item.dataset.failed
  })
}

//產出檔名帶球員名與本地時間，存到手機裡才分得出是誰的、哪一次
const reportName = (now) => {
  const pad = (n) => String(n).padStart(2, '0')
  const who = state.player || ''
  return `${who}配球對照表-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}` +
    `-${pad(now.getHours())}${pad(now.getMinutes())}.html`
}

//步驟 8：從虛擬檔案系統讀回報表，做成 Blob URL；舊的先釋放，避免重跑時記憶體一直長
const showReport = () => {
  const bytes = state.pyodide.FS.readFile(OUTPUT_PATH)
  const blob = new Blob([bytes], { type: 'text/html;charset=utf-8' })
  if (state.reportUrl) URL.revokeObjectURL(state.reportUrl)
  state.reportUrl = URL.createObjectURL(blob)
  const label = `${state.player || ''}配球對照表`
  const open = el('open-report')
  open.textContent = `開啟${label}`
  el('save-report').textContent = `下載${label}`
  open.href = state.reportUrl
  open.target = '_blank'
  open.rel = 'noopener'
  const save = el('save-report')
  save.href = state.reportUrl
  save.setAttribute('download', reportName(new Date()))
  el('result').hidden = false
}

//讓瀏覽器先把「處理中」畫出來；管線在主執行緒同步跑，跑的期間畫面不會重繪
const nextFrame = () => new Promise((resolve) => setTimeout(resolve, 30))

//步驟 6–9：讀檔成位元組、跑管線、顯示結果
const run = async () => {
  el('run').disabled = true
  el('error').hidden = true
  el('result').hidden = true
  el('log').textContent = ''
  el('log').hidden = false
  el('progress').hidden = false
  resetProgress()
  try {
    logRosterDates()
    const entries = await Promise.all(usableFiles().map(async (file) =>
      [file.name, new Uint8Array(await file.arrayBuffer())]))
    await nextFrame()
    const webRun = state.pyodide.globals.get('web_run')
    const sink = (text) => {
      const event = JSON.parse(text)
      appendLog(event)
      updateProgress(event)
    }
    const result = JSON.parse(webRun(entries, sink, OUTPUT_PATH))
    webRun.destroy()
    state.player = result.player || ''
    if (result.ok) {
      showReport()
    } else {
      showError(`產出 HTML 失敗：${result.errors.map((e) => e.msg).join('；')}`)
    }
  } catch (error) {
    showError(error)
  } finally {
    el('run').disabled = usableFiles().length === 0
  }
}

const bind = () => {
  el('files').addEventListener('change', (event) => {
    state.picked = Array.from(event.target.files)
    renderFiles()
  })
  el('run').addEventListener('click', run)
}

//離線快取是加分項：註冊失敗只記在 log，不擋主要功能
const registerWorker = () => {
  if (!('serviceWorker' in navigator)) return
  navigator.serviceWorker.register('sw.js').catch((error) => {
    appendLog({ ts: new Date().toISOString().slice(0, 19), stage: 'S1', level: 'warn',
      msg: `離線快取註冊失敗：${error.message}` })
  })
}

bind()
registerWorker()
boot().catch((error) => {
  bootMsg('執行環境載入失敗。')
  el('log').hidden = false
  showError(error)
})
