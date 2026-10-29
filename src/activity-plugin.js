/**
 * minecraft-activity — Hermes desktop plugin.
 * __GENERATED__
 *
 * Shows what Hermes is actually doing (thinking, reading a file, running a
 * command, searching the web, waiting for you, ...) as a Minecraft-style
 * animated icon: in the status bar with a short label, and in the chat's
 * "thinking" row. It only reads the desktop app's gateway events — it never
 * reads message text — and it only shows while a minecraft* theme is applied.
 *
 * Install: <hermes home>/desktop-plugins/minecraft-activity/plugin.js
 * The plugin runs inside each desktop app, so a laptop that connects to
 * another computer's Hermes needs it installed on the laptop too.
 */
import { atom, host, STATUSBAR_AREAS, useValue } from '@hermes/plugin-sdk'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'minecraft-activity'
const ATLAS = '__ATLAS__'
const KINDS = __KINDS__
const LABEL = Object.fromEntries(KINDS.map(k => [k.kind, k.label]))
const STALE_MS = 10 * 60 * 1000
const BENCH = '__BENCH__'
const BENCH_ROWS = __BENCH_ROWS__

// Hermes tool name -> activity kind. Unknown tools fall back to 'tool'.
const TOOL_KIND = [
  [/^(terminal|process_manage|read_terminal|close_terminal|execute_code)$/, 'shell'],
  [/^(web_search|x_search)$/, 'web'],
  [/^(web_extract|browser_)/, 'browse'],
  [/^(read_file|skill_view|skills_list|session_search|feishu_doc_read)$/, 'read'],
  [/^search_files$/, 'search'],
  [/^(write_file|patch|skill_manage)$/, 'edit'],
  [/^(vision_analyze|video_analyze|read_window_below|computer_use)$/, 'vision'],
  [/(memory|todo|cronjob)/, 'memory'],
  [/^(delegate_task|a2a_)/, 'agent'],
  [/^clarify$/, 'wait']
]

export function toolKind(name) {
  const full = String(name || '').toLowerCase()
  const bare = full.split('__').pop()
  for (const [re, kind] of TOOL_KIND) {
    if (re.test(bare) || re.test(full)) {
      return kind
    }
  }
  return 'tool'
}

// ---- per-session activity state ---------------------------------------------------
const sessions = new Map()
const $view = atom({ kind: '', label: '', count: 0 })
let flashTimer = null

function sessionState(sid) {
  let s = sessions.get(sid)
  if (!s) {
    s = { phase: null, tools: new Map(), drafting: null, wait: false, flash: null, at: 0 }
    sessions.set(sid, s)
  }
  return s
}

function reset(s) {
  s.phase = null
  s.tools.clear()
  s.drafting = null
  s.wait = false
}

function busy(s, now) {
  return (s.flash && s.flash.until > now) || s.wait || s.tools.size > 0 || s.drafting || s.phase
}

function pick(now) {
  for (const [sid, s] of sessions) {
    if (now - s.at > STALE_MS) {
      sessions.delete(sid)
    }
  }
  const focused = host.state?.focusedSessionId?.get?.() || null
  let s = focused ? sessions.get(focused) : null
  if (!s) {
    // Focused id unknown to us (or none): show the most recently active session.
    for (const cand of sessions.values()) {
      if (busy(cand, now) && (!s || cand.at > s.at)) {
        s = cand
      }
    }
  }
  return s
}

export function current(now = Date.now()) {
  const s = pick(now)
  if (!s) return { kind: '', count: 0 }
  if (s.flash && s.flash.until > now) return { kind: s.flash.kind, count: 0 }
  if (s.wait) return { kind: 'wait', count: 0 }
  if (s.tools.size) {
    const names = [...s.tools.values()]
    return { kind: toolKind(names[names.length - 1]), count: s.tools.size }
  }
  if (s.drafting) return { kind: toolKind(s.drafting), count: 0 }
  if (s.phase) return { kind: s.phase, count: 0 }
  return { kind: '', count: 0 }
}

function refresh() {
  const { kind, count } = current()
  const prev = $view.get()
  if (prev.kind !== kind || prev.count !== count) {
    $view.set({ kind, count, label: kind ? LABEL[kind] || '' : '' })
  }
  const root = document.documentElement
  if (kind) root.dataset.mcActivity = kind
  else delete root.dataset.mcActivity
}

function flash(s, kind, ms) {
  s.flash = { kind, until: Date.now() + ms }
  clearTimeout(flashTimer)
  flashTimer = setTimeout(refresh, ms + 50)
}

export function onEvent(ev) {
  if (!ev || ev.replayed || !ev.session_id) return
  const s = sessionState(ev.session_id)
  const p = ev.payload || {}
  switch (ev.type) {
    case 'message.start':
      s.phase = 'think'
      s.flash = null
      s.wait = false
      break
    case 'reasoning.delta':
    case 'thinking.delta':
    case 'reasoning.available':
      s.phase = 'think'
      break
    case 'message.delta':
      s.phase = 'write'
      break
    case 'tool.generating':
      s.drafting = p.name || 'tool'
      break
    case 'tool.start':
      s.tools.set(p.tool_id || `${p.name}#${s.tools.size}`, p.name || '')
      s.drafting = null
      break
    case 'tool.complete': {
      if (p.tool_id && s.tools.has(p.tool_id)) {
        s.tools.delete(p.tool_id)
      } else {
        for (const [id, name] of s.tools) {
          if (name === p.name) {
            s.tools.delete(id)
            break
          }
        }
      }
      break
    }
    case 'approval.request':
    case 'clarify.request':
      s.wait = true
      break
    case 'approval.received':
    case 'approval.respond':
    case 'approval.settled':
    case 'approval.cancelled':
    case 'clarify.respond':
    case 'clarify.settled':
      s.wait = false
      break
    case 'message.complete':
      reset(s)
      flash(s, 'done', 1500)
      break
    case 'error':
      reset(s)
      flash(s, 'error', 3000)
      break
    default:
      return
  }
  s.at = Date.now()
  refresh()
}


// ---- workbench: four stations above the composer, a mini copy of your pet walks to the active one
const STATIONS = ['lectern', 'forge', 'map', 'store']
const STATION_OF = {
  think: 'lectern', read: 'lectern', write: 'lectern',
  edit: 'forge', shell: 'forge', tool: 'forge',
  web: 'map', browse: 'map', search: 'map', vision: 'map',
  memory: 'store', wait: 'store', agent: 'store'
}
const PET_POSE = {
  think: 'review', read: 'review', write: 'review', edit: 'running', shell: 'running', tool: 'running',
  web: 'review', browse: 'review', search: 'review', vision: 'review', memory: 'review',
  wait: 'waiting', agent: 'waving', done: 'waving', error: 'failed', idle: 'idle'
}
// CSS-pixel layout: stations on a shelf, the pet walks on the floor below them
const TILE = 32, GAP = 12, PAD = 4, SHELF = 34, BH = 66, PET_H = 30, SPEED = 70
const BW = PAD * 2 + TILE * 4 + GAP * 3
const stationX = i => PAD + i * (TILE + GAP)

export class Workbench {
  constructor(request) {
    this.request = request
    this.canvas = document.createElement('canvas')
    this.canvas.id = 'hmt-bench'
    Object.assign(this.canvas.style, {
      position: 'fixed', width: `${BW}px`, height: `${BH}px`, pointerEvents: 'none', zIndex: '5', display: 'none'
    })
    document.body.appendChild(this.canvas)
    this.ctx = this.canvas.getContext('2d')
    this.atlas = new Image()
    this.atlas.src = BENCH
    this.pet = null          // { img, fw, fh, rows, frames, loop }
    this.petRev = ''
    this.petX = stationX(0) + TILE / 2
    this.lastStation = 0
    this.last = 0
    this.raf = 0
    this.frames = 0
    this.visible = false
    this.reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')
  }

  async loadPet() {
    try {
      const info = await this.request('pet.info', this.petRev ? { knownRevision: this.petRev } : {})
      if (!info || !info.enabled) {
        this.pet = null
        this.petRev = ''
        return
      }
      if (info.spritesheetUnchanged && this.pet) return
      if (!info.spritesheetBase64) return
      const img = new Image()
      img.src = `data:${info.mime || 'image/png'};base64,${info.spritesheetBase64}`
      const rows = info.stateRows || ['idle', 'running-right', 'running-left', 'waving', 'jumping', 'failed', 'waiting', 'running', 'review']
      this.pet = {
        img, rows, fw: info.frameW || 192, fh: info.frameH || 208, loop: info.loopMs || 1100,
        frames: name => (info.framesByRow && info.framesByRow[name]) || (info.framesByState && info.framesByState[name]) || info.framesPerState || 6
      }
      this.petRev = info.spritesheetRevision || ''
    } catch {
      /* pet RPC unavailable: draw the stations only */
    }
  }

  /** Place the canvas on the composer's top-right edge; hide when there is no room or no minecraft theme. */
  place() {
    const themed = document.documentElement.dataset.mcTheme === '1'
    let best = null
    if (themed) {
      for (const el of document.querySelectorAll('[data-slot="composer-surface"]')) {
        const r = el.getBoundingClientRect()
        if (r.width >= 420 && r.height > 0 && (!best || r.width > best.width)) best = r
      }
    }
    this.visible = Boolean(best)
    this.canvas.style.display = this.visible ? 'block' : 'none'
    if (best) {
      this.canvas.style.left = `${Math.round(best.right - BW - 14)}px`
      this.canvas.style.top = `${Math.round(best.top - BH + 4)}px`
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      if (this.canvas.width !== BW * dpr) {
        this.canvas.width = BW * dpr
        this.canvas.height = BH * dpr
      }
    }
    return this.visible
  }

  petRow(name) {
    const rows = this.pet.rows
    for (const n of [name, name === 'running' ? 'running-right' : '', 'idle']) {
      const i = n ? rows.indexOf(n) : -1
      if (i >= 0) return { i, name: n }
    }
    return { i: 0, name: rows[0] }
  }

  /** Draw one frame for wall-clock time `now` (ms). Deterministic for a given state + now. */
  draw(now) {
    const { ctx } = this
    const dt = this.last ? Math.min(0.1, (now - this.last) / 1000) : 0
    this.last = now
    const still = this.reduced?.matches
    const kind = current().kind || 'idle'
    const station = STATION_OF[kind]
    if (station) this.lastStation = STATIONS.indexOf(station)
    const target = stationX(this.lastStation) + TILE / 2
    const diff = target - this.petX
    const moving = !still && Math.abs(diff) > 1
    this.petX = still ? target : this.petX + Math.sign(diff) * Math.min(Math.abs(diff), SPEED * dt)

    const dpr = this.canvas.width / BW
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, BW, BH)
    ctx.imageSmoothingEnabled = false
    ctx.fillStyle = 'rgba(110,72,36,0.9)'
    ctx.fillRect(0, SHELF, BW, 2)
    ctx.fillStyle = 'rgba(0,0,0,0.35)'
    ctx.fillRect(0, SHELF + 2, BW, 1)
    const f = still ? 0 : Math.floor(now / 125) % 8
    if (this.atlas.complete && this.atlas.naturalWidth) {
      STATIONS.forEach((name, i) => {
        const active = i === this.lastStation && station === name
        if (active) {
          const glow = ctx.createRadialGradient(stationX(i) + TILE / 2, SHELF - TILE / 2, 2, stationX(i) + TILE / 2, SHELF - TILE / 2, TILE * 0.75)
          glow.addColorStop(0, 'rgba(255,230,140,0.30)')
          glow.addColorStop(1, 'rgba(255,230,140,0)')
          ctx.fillStyle = glow
          ctx.fillRect(stationX(i) - 6, 0, TILE + 12, SHELF)
          ctx.fillStyle = 'rgba(255,214,96,0.95)'
          ctx.fillRect(stationX(i) + 4, SHELF, TILE - 8, 2)
        }
        const row = BENCH_ROWS.indexOf(active ? `${name}-${kind}` : `${name}-idle`)
        ctx.drawImage(this.atlas, (active ? f : 0) * 16, row * 16, 16, 16, stationX(i), SHELF - TILE, TILE, TILE)
      })
      if (kind === 'done' || kind === 'error') {
        const row = BENCH_ROWS.indexOf(`fx-${kind}`)
        ctx.drawImage(this.atlas, f * 16, row * 16, 16, 16, stationX(this.lastStation), SHELF - TILE, TILE, TILE)
      }
    }
    if (this.pet && this.pet.img.complete && this.pet.img.naturalWidth) {
      const p = this.pet
      let pose = moving ? (diff > 0 ? 'running-right' : 'running-left') : PET_POSE[kind] || 'idle'
      let mirror = false
      if (moving && p.rows.indexOf(pose) < 0) {
        mirror = diff < 0
        pose = 'running'
      }
      const r = this.petRow(pose)
      const n = p.frames(r.name)
      const col = still ? 0 : Math.floor((now % p.loop) / (p.loop / n)) % n
      const h = PET_H
      const w = (p.fw / p.fh) * h
      ctx.imageSmoothingEnabled = true
      ctx.save()
      ctx.translate(this.petX, BH - h)
      if (mirror) ctx.scale(-1, 1)
      ctx.drawImage(p.img, col * p.fw, r.i * p.fh, p.fw, p.fh, -w / 2, 0, w, h)
      ctx.restore()
    }
  }

  start() {
    const loop = now => {
      this.raf = requestAnimationFrame(loop)
      if (document.hidden || !this.visible) return
      if (now - this.last >= 45) {
        if (++this.frames % 10 === 0) this.place()
        this.draw(now)
      }
    }
    cancelAnimationFrame(this.raf)
    this.raf = requestAnimationFrame(loop)
  }

  destroy() {
    cancelAnimationFrame(this.raf)
    this.canvas.remove()
  }
}

// ---- theme detection + styles ---------------------------------------------------------
function detectTheme() {
  const root = document.documentElement
  const on = getComputedStyle(root).getPropertyValue('--mc-think').trim() !== ''
  if (on) root.dataset.mcTheme = '1'
  else delete root.dataset.mcTheme
}

const H = KINDS.length * 16
const ON = 'html[data-mc-theme="1"]'
export const CSS = [
  `:root{--hmt-atlas:url("${ATLAS}")}`,
  '.hmt-chip{display:none;align-items:center;gap:6px;height:100%;padding:0 8px;font-size:11px;line-height:1;white-space:nowrap}',
  `${ON} .hmt-chip[data-kind]{display:inline-flex}`,
  `.hmt-ico{flex:none;width:16px;height:16px;background:var(--hmt-atlas) 0 0/128px ${H}px no-repeat;image-rendering:pixelated;animation:hmt-ico 1s steps(8) infinite}`,
  '@keyframes hmt-ico{to{background-position-x:-128px}}',
  ...KINDS.map((k, i) => `.hmt-ico[data-kind="${k.kind}"]{background-position-y:-${i * 16}px}`),
  // the chat's thinking row (pre-first-token) and the quiet-gap activity row
  `${ON}[data-mc-activity] [data-slot="aui_response-loading"]::before{background-image:var(--hmt-atlas)!important;background-size:256px ${H * 2}px!important}`,
  `${ON}[data-mc-activity] [data-slot="aui_turn-activity"][data-state="active"]::before{content:"";display:inline-block;flex:none;width:32px;height:32px;margin-right:8px;vertical-align:middle;background:var(--hmt-atlas) 0 0/256px ${H * 2}px no-repeat;image-rendering:pixelated;animation:hmt-big 1.2s steps(8) infinite}`,
  '@keyframes hmt-big{to{background-position-x:-256px}}',
  ...KINDS.map(
    (k, i) =>
      `${ON}[data-mc-activity="${k.kind}"] [data-slot="aui_response-loading"]::before,` +
      `${ON}[data-mc-activity="${k.kind}"] [data-slot="aui_turn-activity"][data-state="active"]::before` +
      `{background-position-y:-${i * 32}px!important}`
  ),
  '@media (prefers-reduced-motion:reduce){.hmt-ico,[data-slot="aui_turn-activity"]::before{animation:none!important}}'
].join('\n')

function ActivityChip() {
  const v = useValue($view)
  const kind = v.kind || undefined
  return jsxs('span', {
    className: 'hmt-chip',
    'data-kind': kind,
    title: v.label,
    children: [
      jsx('span', { className: 'hmt-ico', 'data-kind': kind }),
      jsx('span', { children: v.count > 1 ? `${v.label} ×${v.count}` : v.label })
    ]
  })
}

export default {
  id: ID,
  name: 'Minecraft Activity',
  register(ctx) {
    let style = document.getElementById('hmt-activity-css')
    if (!style) {
      style = document.createElement('style')
      style.id = 'hmt-activity-css'
      document.head.appendChild(style)
    }
    style.textContent = CSS
    detectTheme()
    document.getElementById('hmt-bench')?.remove()
    const request = (method, params) => host.request(method, params)
    const bench = new Workbench(request)
    window.__hmtBench = bench
    bench.place()
    bench.loadPet()
    bench.start()
    let ticks = 0
    const tick = setInterval(() => {
      detectTheme()
      refresh()
      bench.place()
      if (++ticks % 8 === 0) bench.loadPet()
    }, 2000)
    const placeOnResize = () => bench.place()
    window.addEventListener('resize', placeOnResize)
    const subscribe = ctx.onEvent || host.onEvent
    const unsubscribe = subscribe('*', onEvent)
    ctx.register({ id: 'chip', area: STATUSBAR_AREAS.right, order: 50, render: () => jsx(ActivityChip, {}) })
    ctx.onDispose?.(() => {
      clearInterval(tick)
      window.removeEventListener('resize', placeOnResize)
      bench.destroy()
      clearTimeout(flashTimer)
      if (typeof unsubscribe === 'function') unsubscribe()
      style.remove()
      delete document.documentElement.dataset.mcActivity
      delete document.documentElement.dataset.mcTheme
    })
  }
}
