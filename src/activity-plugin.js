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
const CRITTERS = '__CRITTERS__'
const CRITTER_ROWS = __CRITTER_ROWS__

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


// ---- critters: a few small world-themed mobs roaming the whole window --------------------
const ROSTER = {
  overworld: ['bee', 'bee', 'allay'],
  cherry: ['bee', 'bee', 'allay'],
  nether: ['ghast', 'blaze', 'blaze'],
  end: ['phantom', 'eye', 'eye'],
  snow: ['bat', 'allay', 'bat']
}
const SPEC = { bee: [30, 70], allay: [30, 55], bat: [30, 95], ghast: [44, 32], blaze: [32, 48], eye: [26, 42], phantom: [36, 85] }
const FLEE = 110

function mulberry(seed) {
  let s = seed >>> 0
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export class Critters {
  constructor(seed = Date.now()) {
    this.rand = mulberry(seed)
    this.canvas = document.createElement('canvas')
    this.canvas.id = 'hmt-critters'
    Object.assign(this.canvas.style, {
      position: 'fixed', left: '0px', top: '0px', pointerEvents: 'none', zIndex: '40', opacity: '0.9', display: 'none'
    })
    document.body.appendChild(this.canvas)
    this.ctx = this.canvas.getContext('2d')
    this.atlas = new Image()
    this.atlas.src = CRITTERS
    this.world = ''
    this.list = []
    this.pointer = { x: -1e4, y: -1e4 }
    this.w = 0
    this.h = 0
    this.last = 0
    this.raf = 0
    this.hop = 0
    this.cheered = false
    this.visible = false
    this.reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    this.onMove = e => {
      this.pointer.x = e.clientX
      this.pointer.y = e.clientY
    }
    window.addEventListener('pointermove', this.onMove, { passive: true })
  }

  /** Size to the window; show only under a minecraft skin; respawn when the world changes. */
  place() {
    const root = document.documentElement
    const world = getComputedStyle(root).getPropertyValue('--mc-world').trim().replace(/"/g, '') || 'overworld'
    const w = window.innerWidth
    const h = window.innerHeight
    this.visible = root.dataset.mcTheme === '1' && w > 300 && h > 240
    this.canvas.style.display = this.visible ? 'block' : 'none'
    if (!this.visible) return false
    if (w !== this.w || h !== this.h) {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      this.w = w
      this.h = h
      this.canvas.width = Math.round(w * dpr)
      this.canvas.height = Math.round(h * dpr)
      this.canvas.style.width = `${w}px`
      this.canvas.style.height = `${h}px`
      for (const c of this.list) this.retarget(c)
    }
    if (world !== this.world) {
      this.world = world
      this.spawn()
    }
    return true
  }

  spawn() {
    this.list = (ROSTER[this.world] || ROSTER.overworld).map(name => {
      const [size, speed] = SPEC[name]
      const c = { name, size, speed, x: this.rand() * this.w, y: 30 + this.rand() * (this.h - 60), vx: 0, vy: 0,
        tx: 0, ty: 0, wait: 0, phase: this.rand() * 6.28, face: 1 }
      this.retarget(c)
      return c
    })
  }

  retarget(c) {
    const m = 40
    c.tx = m + this.rand() * Math.max(1, this.w - 2 * m)
    c.ty = m + this.rand() * Math.max(1, this.h - 2 * m)
  }

  step(c, dt, boost) {
    const sp = c.speed * boost
    let ax = 0
    let ay = 0
    if (c.wait > 0) {
      c.wait -= dt
      ax = -c.vx * 2
      ay = -c.vy * 2
    } else {
      const dx = c.tx - c.x
      const dy = c.ty - c.y
      const d = Math.hypot(dx, dy)
      if (d < 14) {
        this.retarget(c)
        c.wait = (0.6 + this.rand() * 2.4) / boost
      } else {
        ax = (dx / d) * sp - c.vx
        ay = (dy / d) * sp - c.vy
      }
    }
    const px = c.x - this.pointer.x
    const py = c.y - this.pointer.y
    const pd = Math.hypot(px, py)
    if (pd < FLEE && pd > 0.01) {
      const k = sp * 4 * (1 - pd / FLEE)
      ax += (px / pd) * k
      ay += (py / pd) * k
      c.wait = 0
    }
    const t = Math.min(1, dt * 2.2)
    c.vx += ax * t
    c.vy += ay * t
    const v = Math.hypot(c.vx, c.vy)
    if (v > sp * 2) {
      c.vx *= (sp * 2) / v
      c.vy *= (sp * 2) / v
    }
    const r = c.size / 2
    c.x = Math.min(this.w - r, Math.max(r, c.x + c.vx * dt))
    c.y = Math.min(this.h - r, Math.max(r, c.y + c.vy * dt))
    if (Math.abs(c.vx) > 4) c.face = c.vx >= 0 ? 1 : -1
  }

  /** Advance and draw for wall-clock time `now` (ms). */
  draw(now) {
    const dt = this.last ? Math.min(0.1, (now - this.last) / 1000) : 0
    this.last = now
    const kind = current().kind
    const busy = Boolean(kind) && kind !== 'done' && kind !== 'error'
    const boost = busy ? 1.7 : 1
    if (kind === 'done' && !this.cheered) {
      this.cheered = true
      this.hop = 1
    } else if (kind !== 'done') {
      this.cheered = false
    }
    this.hop = Math.max(0, this.hop - dt * 1.6)
    const still = this.reduced?.matches
    const { ctx } = this
    const dpr = this.canvas.width / Math.max(1, this.w)
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, this.w, this.h)
    if (!(this.atlas.complete && this.atlas.naturalWidth)) return
    ctx.imageSmoothingEnabled = false
    const f = still ? 0 : Math.floor(now / (busy ? 80 : 130)) % 8
    for (const c of this.list) {
      if (!still) this.step(c, dt, boost)
      const bob = still ? 0 : Math.sin((now / 1000) * 3 + c.phase) * 3 - Math.sin(this.hop * Math.PI) * 16
      const row = CRITTER_ROWS.indexOf(c.name)
      ctx.save()
      ctx.translate(Math.round(c.x), Math.round(c.y + bob))
      ctx.scale(c.face, 1)
      ctx.drawImage(this.atlas, f * 16, row * 16, 16, 16, -c.size / 2, -c.size / 2, c.size, c.size)
      ctx.restore()
    }
  }

  start() {
    const loop = now => {
      this.raf = requestAnimationFrame(loop)
      if (document.hidden || !this.visible) {
        this.last = 0
        return
      }
      if (now - this.last >= 33) this.draw(now)
    }
    cancelAnimationFrame(this.raf)
    this.raf = requestAnimationFrame(loop)
  }

  destroy() {
    cancelAnimationFrame(this.raf)
    window.removeEventListener('pointermove', this.onMove)
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
    document.getElementById('hmt-critters')?.remove()
    const critters = new Critters()
    window.__hmtCritters = critters
    critters.place()
    critters.start()
    const tick = setInterval(() => {
      detectTheme()
      refresh()
      critters.place()
    }, 2000)
    const placeOnResize = () => critters.place()
    window.addEventListener('resize', placeOnResize)
    const subscribe = ctx.onEvent || host.onEvent
    const unsubscribe = subscribe('*', onEvent)
    ctx.register({ id: 'chip', area: STATUSBAR_AREAS.right, order: 50, render: () => jsx(ActivityChip, {}) })
    ctx.onDispose?.(() => {
      clearInterval(tick)
      window.removeEventListener('resize', placeOnResize)
      critters.destroy()
      clearTimeout(flashTimer)
      if (typeof unsubscribe === 'function') unsubscribe()
      style.remove()
      delete document.documentElement.dataset.mcActivity
      delete document.documentElement.dataset.mcTheme
    })
  }
}
