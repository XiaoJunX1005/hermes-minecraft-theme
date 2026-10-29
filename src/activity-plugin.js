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
import { atom, host, PALETTE_AREA, STATUSBAR_AREAS, useValue } from '@hermes/plugin-sdk'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'minecraft-activity'
const ATLAS = '__ATLAS__'
const KINDS = __KINDS__
const LABEL = Object.fromEntries(KINDS.map(k => [k.kind, k.label]))
const STALE_MS = 10 * 60 * 1000
const CRITTERS = '__CRITTERS__'
const CRITTER_ROWS = __CRITTER_ROWS__
const WORLD_CSS = __WORLD_CSS__
const WORLD_INFO = __WORLD_INFO__

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


// ---- critters: small world-themed mobs roaming the whole window ------------------------
// size: 2x or 3x the 16px sprite so pixels stay square. turns: has a front view for the turn animation.
const SPECIES = {
  bee:     { size: 32, speed: 60, turn: 3.2, wander: 1.6, pause: [0.5, 1.8], pauseChance: 0.55, bob: 2.5, fps: 14, turns: true, max: 4 },
  parrot:  { size: 32, speed: 75, turn: 2.2, wander: 0.9, pause: [0.4, 1.2], pauseChance: 0.25, bob: 2, fps: 10, turns: true, max: 2 },
  allay:   { size: 32, speed: 45, turn: 1.8, wander: 0.8, pause: [0.8, 2.2], pauseChance: 0.35, bob: 4, fps: 8, turns: true, max: 2 },
  phantom: { size: 48, speed: 85, turn: 0.9, wander: 0.4, pause: [0, 0], pauseChance: 0, bob: 1.5, fps: 6, turns: true, max: 2 },
  dragon:  { size: 48, speed: 70, turn: 0.8, wander: 0.35, pause: [0, 0], pauseChance: 0, bob: 2, fps: 6, turns: true, max: 1 },
  bat:     { size: 32, speed: 90, turn: 4.5, wander: 3, pause: [0.2, 0.6], pauseChance: 0.15, bob: 2, fps: 16, turns: false, max: 3 },
  ghast:   { size: 48, speed: 22, turn: 0.6, wander: 0.3, pause: [1.5, 4], pauseChance: 0.6, bob: 3, fps: 5, turns: false, max: 1, calm: true },
  shulker: { size: 32, speed: 0, turn: 0, wander: 0, pause: [0, 0], pauseChance: 0, bob: 0, fps: 0, turns: false, max: 4, env: true },
  blaze:   { size: 32, speed: 28, turn: 1.2, wander: 0.5, pause: [1.2, 3.5], pauseChance: 0.7, bob: 5, fps: 9, turns: false, max: 2, calm: true }
}
const POOLS = {
  overworld: { n: [2, 5], pick: [['bee', 5], ['bee-pollen', 3], ['bee-angry', 1], ['allay', 2], ['parrot-red', 1], ['parrot-blue', 1], ['parrot-green', 1]] },
  cherry: { n: [2, 5], pick: [['bee', 4], ['bee-pollen', 4], ['allay', 2], ['parrot-cyan', 1], ['parrot-gray', 1]] },
  snow: { n: [2, 4], pick: [['allay', 3], ['bat', 2], ['phantom', 1]] },
  nether: { n: [2, 4], pick: [['ghast', 1], ['blaze', 3]] },
  end: { n: [2, 3], pick: [['phantom', 2], ['dragon', 1]] }
}
const TURN = 0.36
const speciesOf = v => v.split('-')[0]
const worldOf = () =>
  getComputedStyle(document.documentElement).getPropertyValue('--mc-world').trim().replace(/"/g, '') || 'overworld'

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
      position: 'fixed', left: '0px', top: '0px', pointerEvents: 'none', zIndex: '40', opacity: '0.92', display: 'none'
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
    this.t = 0
    this.last = 0
    this.raf = 0
    this.hop = 0
    this.cheered = false
    this.churnAt = 0
    this.visible = false
    this.reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    this.onMove = e => {
      this.pointer.x = e.clientX
      this.pointer.y = e.clientY
    }
    window.addEventListener('pointermove', this.onMove, { passive: true })
  }

  place() {
    const root = document.documentElement
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
    const world = worldOf()
    if (world !== this.world) {
      this.world = POOLS[world] ? world : 'overworld'
      this.spawn()
    }
    return true
  }

  pickVariant(counts) {
    const pool = POOLS[this.world] || POOLS.overworld
    const ok = pool.pick.filter(([v]) => (counts[speciesOf(v)] || 0) < (SPECIES[speciesOf(v)].max || 3))
    const total = ok.reduce((a, [, wt]) => a + wt, 0)
    let r = this.rand() * total
    for (const [v, wt] of ok) {
      if ((r -= wt) <= 0) return v
    }
    return ok.length ? ok[ok.length - 1][0] : null
  }

  make(v, fromEdge) {
    const sp = speciesOf(v)
    const S = SPECIES[sp]
    const c = { v, sp, x: 0, y: 0, h: 0, spd: S.speed * 0.6, tx: 0, ty: 0, wait: 0, face: 1, nextFace: 1, turnT: -1,
      lastTurn: -9, flip: 0, idle: 0, noise: 0, phase: this.rand() * 6.28, state: 'fly' }
    if (fromEdge) {
      const e = Math.floor(this.rand() * 4)
      c.x = e === 0 ? -30 : e === 1 ? this.w + 30 : this.rand() * this.w
      c.y = e === 2 ? -30 : e === 3 ? this.h + 30 : 40 + this.rand() * (this.h - 80)
      c.state = 'enter'
    } else {
      c.x = 48 + this.rand() * Math.max(1, this.w - 96)
      c.y = 48 + this.rand() * Math.max(1, this.h - 96)
    }
    this.retarget(c)
    c.h = Math.atan2(c.ty - c.y, c.tx - c.x)
    c.face = c.nextFace = Math.cos(c.h) >= 0 ? 1 : -1
    return c
  }

  spawn(forceMode) {
    if (this.world === 'end') {
      this.list = []
      this.endMode = forceMode || (this.rand() < 0.5 ? 'main' : 'outer')
      if (this.endMode === 'main') {
        this.list.push(this.make('dragon', false))
        if (this.rand() < 0.6) this.list.push(this.make('phantom', false))
      } else {
        if (this.rand() < 0.5) this.list.push(this.make('phantom', false))
        const n = 2 + Math.floor(this.rand() * 3)
        for (let i = 0; i < n; i++) {
          this.list.push({ v: 'shulker', sp: 'shulker', x: -999, y: -999, perch: -1, state: 'sit', open: 0, target: 0,
            openT: this.rand() * 3, near: 0, cool: 0, alpha: 1, st: 0, teleports: 0, phase: this.rand() * 6.28, face: 1, turnT: -1, idle: 0 })
        }
      }
      this.churnAt = Infinity
      return
    }
    this.endMode = ''
    const pool = POOLS[this.world] || POOLS.overworld
    const n = pool.n[0] + Math.floor(this.rand() * (pool.n[1] - pool.n[0] + 1))
    const counts = {}
    this.list = []
    for (let i = 0; i < n; i++) {
      const v = this.pickVariant(counts)
      if (!v) break
      counts[speciesOf(v)] = (counts[speciesOf(v)] || 0) + 1
      this.list.push(this.make(v, false))
    }
    this.churnAt = this.t + 40 + this.rand() * 70
  }

  /** Every minute or two one mob flies off-screen or a new one flies in, within the world's range. */
  churn() {
    const pool = POOLS[this.world] || POOLS.overworld
    const live = this.list.filter(c => c.state !== 'leave')
    if (live.length < pool.n[1] && (live.length <= pool.n[0] || this.rand() < 0.5)) {
      const counts = {}
      for (const c of live) counts[c.sp] = (counts[c.sp] || 0) + 1
      const v = this.pickVariant(counts)
      if (v) this.list.push(this.make(v, true))
    } else if (live.length > pool.n[0]) {
      const c = live[Math.floor(this.rand() * live.length)]
      c.state = 'leave'
      const d = [c.x, this.w - c.x, c.y, this.h - c.y]
      const e = d.indexOf(Math.min(...d))
      c.tx = e === 0 ? -120 : e === 1 ? this.w + 120 : c.x
      c.ty = e === 2 ? -120 : e === 3 ? this.h + 120 : c.y
    }
    this.churnAt = this.t + 40 + this.rand() * 70
  }

  /** Shulkers sit on island perches, peek now and then, and teleport away if you hover near them. */
  stepShulker(c, dt) {
    const ps = this.perches ? this.perches() : []
    if (!ps.length) {
      c.x = -999
      return
    }
    const used = new Set(this.list.filter(o => o !== c && o.sp === 'shulker').map(o => o.perch))
    if (c.perch < 0 || c.perch >= ps.length) {
      const free = ps.map((_, i) => i).filter(i => !used.has(i))
      if (!free.length) {
        c.x = -999
        return
      }
      c.perch = free[Math.floor(this.rand() * free.length)]
    }
    c.cool = Math.max(0, c.cool - dt)
    c.x = ps[c.perch].x
    c.y = ps[c.perch].y
    if (c.state === 'sit') {
      c.openT -= dt
      if (c.openT <= 0) {
        c.target = c.target ? 0 : 1
        c.openT = c.target ? 1.2 + this.rand() * 1.5 : 2.5 + this.rand() * 4
      }
      c.open += (c.target - c.open) * Math.min(1, dt * 4)
      const d = Math.hypot(c.x - this.pointer.x, c.y - 14 - this.pointer.y)
      c.near = d < 90 ? c.near + dt : 0
      if (c.near > 0.35 && c.cool <= 0 && dt > 0) {
        c.state = 'hide'
        c.st = 0
      }
      return
    }
    c.st += dt
    if (c.state === 'hide') {
      c.open = Math.max(0, c.open - dt * 6)
      c.alpha = Math.max(0, 1 - c.st / 0.35)
      if (c.st >= 0.35) {
        const opts = ps.map((p, i) => ({ p, i })).filter(({ i }) => !used.has(i) && i !== c.perch)
        const far = opts.filter(({ p }) => Math.hypot(p.x - this.pointer.x, p.y - this.pointer.y) > 160)
        const pool = far.length ? far : opts
        if (pool.length) {
          c.perch = pool[Math.floor(this.rand() * pool.length)].i
          c.teleports++
        }
        c.state = 'show'
        c.st = 0
      }
    } else if (c.state === 'show') {
      c.alpha = Math.min(1, c.st / 0.35)
      if (c.st >= 0.35) {
        c.state = 'sit'
        c.alpha = 1
        c.near = 0
        c.cool = 3 + this.rand() * 3
      }
    }
  }

  retarget(c) {
    const m = 48
    for (let k = 0; k < 4; k++) {
      c.tx = m + this.rand() * Math.max(1, this.w - 2 * m)
      c.ty = m + this.rand() * Math.max(1, this.h - 2 * m)
      if (Math.hypot(c.tx - c.x, c.ty - c.y) > 160) break
    }
  }

  step(c, dt, boost) {
    const S = SPECIES[c.sp]
    const flying = c.state === 'fly'
    let target = Math.atan2(c.ty - c.y, c.tx - c.x)
    let want = S.speed * boost * (c.state === 'leave' ? 1.5 : 1)
    if (flying && c.wait > 0) {
      c.wait -= dt
      want = 0
    }
    const px = c.x - this.pointer.x
    const py = c.y - this.pointer.y
    const pd = Math.hypot(px, py)
    const fleeR = S.calm ? 70 : 120
    if (flying && pd < fleeR) {
      target = Math.atan2(py, px)
      want = S.speed * (S.calm ? 1.3 : 2.2)
      c.wait = 0
    }
    // heading-based steering: each species turns at its own rate, plus a little wander
    c.noise = c.noise * 0.92 + (this.rand() - 0.5) * S.wander * 0.25
    let d = target - c.h
    d = Math.atan2(Math.sin(d), Math.cos(d))
    const maxTurn = S.turn * dt * (pd < fleeR ? 2 : 1)
    c.h += Math.max(-maxTurn, Math.min(maxTurn, d)) + c.noise * dt
    c.spd += (want - c.spd) * Math.min(1, dt * 2.5)
    c.x += Math.cos(c.h) * c.spd * dt
    c.y += Math.sin(c.h) * c.spd * dt
    if (flying) {
      if (Math.hypot(c.tx - c.x, c.ty - c.y) < 24) {
        this.retarget(c)
        if (this.rand() < S.pauseChance) c.wait = (S.pause[0] + this.rand() * (S.pause[1] - S.pause[0])) / boost
      }
      const r = S.size / 2
      if (c.x < r || c.x > this.w - r) {
        c.x = Math.min(this.w - r, Math.max(r, c.x))
        c.h = Math.PI - c.h
        this.retarget(c)
      }
      if (c.y < r || c.y > this.h - r) {
        c.y = Math.min(this.h - r, Math.max(r, c.y))
        c.h = -c.h
        this.retarget(c)
      }
    } else if (c.state === 'enter' && c.x > 40 && c.x < this.w - 40 && c.y > 40 && c.y < this.h - 40) {
      c.state = 'fly'
    }
    c.idle = c.wait > 0 && c.spd < 6 ? c.idle + dt : 0
    // turn animation with hysteresis: only after moving the other way for a moment
    if (c.turnT >= 0) {
      c.turnT += dt
      if (c.turnT >= TURN) {
        c.face = c.nextFace
        c.turnT = -1
        c.lastTurn = this.t
      }
    } else if (S.turns) {
      const vx = Math.cos(c.h) * c.spd
      const dir = vx >= 0 ? 1 : -1
      if (dir !== c.face && Math.abs(vx) > 8) {
        c.flip += dt
        if (c.flip > 0.12 && this.t - c.lastTurn > 0.6) {
          c.turnT = 0
          c.nextFace = dir
          c.flip = 0
        }
      } else {
        c.flip = 0
      }
    }
  }

  draw(now) {
    const dt = this.last ? Math.min(0.1, (now - this.last) / 1000) : 0
    this.last = now
    this.t += dt
    const kind = current().kind
    const busy = Boolean(kind) && kind !== 'done' && kind !== 'error'
    const boost = busy ? 1.6 : 1
    if (kind === 'done' && !this.cheered) {
      this.cheered = true
      this.hop = 1
    } else if (kind !== 'done') {
      this.cheered = false
    }
    this.hop = Math.max(0, this.hop - dt * 1.6)
    const still = this.reduced?.matches
    for (const c of this.list) {
      if (c.sp === 'shulker') this.stepShulker(c, still ? 0 : dt)
      else if (!still) this.step(c, dt, boost)
    }
    if (!still) {
      this.list = this.list.filter(c => !(c.state === 'leave' && (c.x < -60 || c.x > this.w + 60 || c.y < -60 || c.y > this.h + 60)))
      if (this.t >= this.churnAt && this.world !== 'end') this.churn()
    }
    const { ctx } = this
    const dpr = this.canvas.width / Math.max(1, this.w)
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, this.w, this.h)
    if (!(this.atlas.complete && this.atlas.naturalWidth)) return
    ctx.imageSmoothingEnabled = false
    for (const c of this.list) {
      const S = SPECIES[c.sp]
      if (c.sp === 'shulker') {
        if (c.x < -500) continue
        const row = CRITTER_ROWS.indexOf('shulker:front')
        ctx.globalAlpha = c.alpha
        ctx.drawImage(this.atlas, Math.round(c.open * 7) * 16, row * 16, 16, 16, Math.round(c.x - S.size / 2), Math.round(c.y - (S.size * 15) / 16), S.size, S.size)
        ctx.globalAlpha = 1
        if (c.state !== 'sit') {
          ctx.fillStyle = 'rgba(200,130,255,0.85)'
          for (let k = 0; k < 6; k++) {
            const ang = k * 1.05 + this.t * 6
            ctx.fillRect(Math.round(c.x + Math.cos(ang) * 18), Math.round(c.y - 14 + Math.sin(ang) * 12 - c.st * 20), 3, 3)
          }
        }
        continue
      }
      const bob = still ? 0 : Math.sin(this.t * 2.4 + c.phase) * S.bob - Math.sin(this.hop * Math.PI) * 16
      let view = 'front'
      let sx = 1
      let face = c.face
      if (S.turns) {
        view = 'side'
        if (c.turnT >= 0) {
          const p = c.turnT / TURN
          if (p < 1 / 3) sx = 1 - p * 3 * 0.65
          else if (p < 2 / 3) view = 'front'
          else {
            face = c.nextFace
            sx = 0.35 + (p - 2 / 3) * 3 * 0.65
          }
        } else if (c.idle > 0.8) {
          view = 'front'
        }
      }
      const row = CRITTER_ROWS.indexOf(`${c.v}:${view}`)
      if (row < 0) continue
      const f = still ? 0 : Math.floor(this.t * S.fps + c.phase * 3) % 8
      ctx.save()
      ctx.translate(Math.round(c.x), Math.round(c.y + bob))
      if (view === 'side') ctx.scale(face * sx, 1)
      ctx.drawImage(this.atlas, f * 16, row * 16, 16, 16, -S.size / 2, -S.size / 2, S.size, S.size)
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

// ---- scene: a moving pixel background behind the chat, per world ----------------------
// Drawn at 1/3 resolution and scaled up; screen-blended so it only lightens the dark page.
const PX = 3
const PROP_SHEET = '__PROP_SHEET__'
const PROP_BOX = __PROP_BOX__
const SCENES = {
  overworld: { sky: 'rgba(70,140,90,0.16)', shape: 'hills', layers: [['rgba(60,110,80,0.16)', 0.16, 1.2], ['rgba(80,140,90,0.22)', 0.10, 3]],
    props: [['oak', 3], ['birch', 2], ['flowers', 2]], p: 'firefly', n: 16, pc: [210, 255, 120] },
  cherry: { sky: 'rgba(210,110,160,0.16)', shape: 'hills', layers: [['rgba(150,80,120,0.16)', 0.16, 1.2], ['rgba(190,110,150,0.2)', 0.10, 3]],
    props: [['cherry', 4], ['flowers', 1]], p: 'petal', n: 26, pc: [255, 180, 215] },
  snow: { sky: 'rgba(120,160,220,0.16)', shape: 'peaks', layers: [['rgba(110,130,180,0.16)', 0.22, 1], ['rgba(160,180,220,0.2)', 0.12, 2.5]],
    props: [['spruce', 5], ['igloo', 1]], p: 'snow', n: 70, pc: [235, 245, 255] },
  nether: { sky: 'rgba(220,70,30,0.2)', shape: 'pillars', lava: true, layers: [['rgba(120,40,50,0.18)', 0.22, 1], ['rgba(160,50,40,0.22)', 0.13, 2.5]],
    props: [['crimson', 2], ['warped', 2]], p: 'ember', n: 40, pc: [255, 175, 70] },
  end: { sky: 'rgba(130,80,190,0.18)', end: true, layers: [], p: 'mote', n: 26, pc: [200, 150, 255] }
}

export class Scene {
  constructor(seed = Date.now(), getMode = () => 'main') {
    this.rand = mulberry(seed ^ 0x9e3779b9)
    this.getMode = getMode
    this.canvas = document.createElement('canvas')
    this.canvas.id = 'hmt-scene'
    Object.assign(this.canvas.style, {
      position: 'fixed', pointerEvents: 'none', zIndex: '2', mixBlendMode: 'screen', imageRendering: 'pixelated', display: 'none'
    })
    document.body.appendChild(this.canvas)
    this.ctx = this.canvas.getContext('2d')
    this.low = document.createElement('canvas')
    this.lctx = this.low.getContext('2d')
    this.sheet = new Image()
    this.sheet.src = PROP_SHEET
    this.world = ''
    this.mode = ''
    this.rect = { x: 0, y: 0, w: 0, h: 0 }
    this.layers = []
    this.parts = []
    this.end = null
    this.t = 0
    this.last = 0
    this.raf = 0
    this.frames = 0
    this.visible = false
    this.reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')
  }

  place() {
    const root = document.documentElement
    const el = root.dataset.mcTheme === '1' ? document.querySelector('[data-slot="aui_thread-viewport"]') : null
    const r = el?.getBoundingClientRect()
    this.visible = Boolean(r && r.width > 200 && r.height > 120)
    this.canvas.style.display = this.visible ? 'block' : 'none'
    if (!this.visible) return false
    const w = Math.round(r.width)
    const h = Math.round(r.height)
    const resized = w !== this.rect.w || h !== this.rect.h
    if (resized || r.left !== this.rect.x || r.top !== this.rect.y) {
      this.rect = { x: r.left, y: r.top, w, h }
      Object.assign(this.canvas.style, { left: `${r.left}px`, top: `${r.top}px`, width: `${w}px`, height: `${h}px` })
      this.canvas.width = w
      this.canvas.height = h
    }
    const world = SCENES[worldOf()] ? worldOf() : 'overworld'
    const mode = world === 'end' ? this.getMode() || 'main' : ''
    if (resized || world !== this.world || mode !== this.mode) {
      this.world = world
      this.mode = mode
      this.build()
    }
    return true
  }

  heights(shape, L, base, i) {
    const out = new Array(L)
    if (shape === 'pillars') {
      let x = 0
      while (x < L) {
        const w = 3 + Math.floor(this.rand() * 6)
        const hh = Math.round(base * (0.35 + this.rand() * 0.65))
        for (let k = 0; k < w && x < L; k++) out[x++] = hh
        const gap = 2 + Math.floor(this.rand() * 9)
        for (let k = 0; k < gap && x < L; k++) out[x++] = Math.round(base * 0.12)
      }
      return out
    }
    for (let x = 0; x < L; x++) {
      const u = x / L
      let v
      if (shape === 'peaks') {
        const P = 3 + i
        v = 0.25 + 0.75 * (1 - 2 * Math.abs(((u * P + i * 0.37) % 1) - 0.5))
      } else {
        v = 0.6 + 0.25 * Math.sin(2 * Math.PI * (2 * u + i * 0.3)) + 0.15 * Math.sin(2 * Math.PI * (5 * u + i))
      }
      out[x] = Math.round((base * v) / 2) * 2
    }
    for (let x = 0; x < L; x++) out[x] = out[x - (x % 3)]
    return out
  }

  build() {
    const cfg = SCENES[this.world]
    const LW = Math.max(1, Math.ceil(this.rect.w / PX))
    const LH = Math.max(1, Math.ceil(this.rect.h / PX))
    this.low.width = LW
    this.low.height = LH
    this.LW = LW
    this.LH = LH
    const L = LW * 2
    this.layers = cfg.layers.map(([color, frac, speed], i) => ({ color, speed, L, hts: this.heights(cfg.shape, L, LH * frac, i), props: [] }))
    const front = this.layers[this.layers.length - 1]
    if (front && cfg.props) {
      const total = cfg.props.reduce((a, [, w]) => a + w, 0)
      let x = 10 + this.rand() * 20
      while (x < L - 30) {
        let r = this.rand() * total
        let name = cfg.props[0][0]
        for (const [n, w] of cfg.props) {
          if ((r -= w) <= 0) {
            name = n
            break
          }
        }
        front.props.push({ name, x: Math.round(x) })
        x += PROP_BOX[name][2] + 12 + this.rand() * 45
      }
    }
    this.end = cfg.end ? this.buildEnd() : null
    this.parts = Array.from({ length: cfg.n }, () => this.particle(cfg.p, true))
  }

  /** End: 'main' = the main island (obsidian pillars, crystals, exit portal); 'outer' = outer islands (chorus, End city). */
  buildEnd() {
    const { LW, LH } = this
    const r = this.rand
    if (this.mode === 'main') {
      const ground = Array.from({ length: LW }, (_, x) =>
        Math.round(LH * (0.09 + 0.03 * Math.sin((x / LW) * Math.PI * 3) + 0.015 * Math.sin(x / 7))))
      const n = 7
      const pillars = []
      for (let i = 0; i < n; i++) {
        const u = (i + 0.5) / n
        const edge = Math.abs(u - 0.5) * 2
        pillars.push({ x: Math.round(u * LW), w: 7 + Math.floor(r() * 3), h: Math.round(LH * (0.2 + 0.3 * edge + r() * 0.08)),
          cage: i === 1 || i === n - 2, ph: r() * 6.28 })
      }
      return { mode: 'main', ground, pillars }
    }
    const defs = [[0.12, 0.70, 0.20], [0.86, 0.60, 0.20], [0.50, 0.86, 0.28], [0.16, 0.30, 0.11], [0.84, 0.24, 0.12]]
    const islands = defs.map(([u, v, wf]) => {
      const w = Math.max(12, Math.round(LW * wf))
      const rows = []
      let half = w / 2
      const depth = Math.max(4, Math.round(w * 0.32))
      for (let k = 0; k < depth; k++) {
        rows.push(Math.max(1, Math.round(half)))
        half *= 0.84 - r() * 0.08
      }
      return { cx: Math.round(u * LW), top: Math.round(v * LH), rows, props: [], perches: [], ph: r() * 6.28 }
    })
    islands[1].props.push({ name: 'endcity', dx: Math.round(-islands[1].rows[0] * 0.35) })
    islands[0].props.push({ name: 'chorus', dx: Math.round(-islands[0].rows[0] * 0.45) })
    islands[2].props.push({ name: 'chorus', dx: Math.round(islands[2].rows[0] * 0.55) })
    for (const isl of islands) {
      const half = isl.rows[0]
      for (const f of [-0.6, -0.2, 0.2, 0.6]) {
        const dx = Math.round(f * half)
        if (isl.props.some(p => Math.abs(p.dx - dx) < PROP_BOX[p.name][2] / 2 + 5)) continue
        isl.perches.push(dx)
      }
    }
    return { mode: 'outer', islands }
  }

  bob(isl) {
    return this.reduced?.matches ? 0 : Math.round(Math.sin(this.t * 0.35 + isl.ph))
  }

  /** Window-space points where shulkers can sit (outer End only). */
  perches() {
    if (!this.visible || !this.end || this.end.mode !== 'outer') return []
    const out = []
    for (const isl of this.end.islands) {
      const b = this.bob(isl)
      for (const dx of isl.perches) out.push({ x: this.rect.x + (isl.cx + dx) * PX, y: this.rect.y + (isl.top + b) * PX })
    }
    return out
  }

  prop(g, name, x, y, alpha) {
    if (!(this.sheet.complete && this.sheet.naturalWidth)) return
    const [bx, by, w, h] = PROP_BOX[name]
    g.globalAlpha = alpha
    g.drawImage(this.sheet, bx, by, w, h, Math.round(x), Math.round(y), w, h)
    g.globalAlpha = 1
  }

  particle(type, anywhere) {
    const { LW, LH } = this
    const r = this.rand
    const p = { x: r() * LW, y: anywhere ? r() * LH : 0, vx: 0, vy: 0, ph: r() * 6.28, life: 1, s: 1 }
    if (type === 'firefly') {
      p.y = LH * (0.35 + r() * 0.6)
      p.vx = (r() - 0.5) * 3
      p.vy = (r() - 0.5) * 2
    } else if (type === 'petal') {
      p.vy = 3 + r() * 5
      p.vx = -2 - r() * 3
    } else if (type === 'snow') {
      p.s = r() < 0.3 ? 2 : 1
      p.vy = p.s === 2 ? 7 + r() * 4 : 3 + r() * 3
      p.vx = -1 + r() * 0.6
    } else if (type === 'ember') {
      p.y = anywhere ? LH * (0.4 + r() * 0.6) : LH
      p.vy = -(4 + r() * 6)
      p.vx = (r() - 0.5) * 2
      p.life = anywhere ? r() : 1
      p.s = r() < 0.4 ? 2 : 1
    } else {
      p.vy = -(0.6 + r() * 1.4)
      p.vx = (r() - 0.5) * 0.6
      if (!anywhere) p.y = LH
    }
    return p
  }

  drawEnd(g) {
    const E = this.end
    const { LW, LH } = this
    if (E.mode === 'main') {
      for (const p of E.pillars) {
        const top = LH - p.h
        const x0 = p.x - (p.w >> 1)
        g.fillStyle = 'rgba(100,70,150,0.34)'
        g.fillRect(x0, top, p.w, p.h)
        g.fillStyle = 'rgba(60,40,100,0.30)'
        g.fillRect(x0 + p.w - 2, top, 2, p.h)
        g.fillStyle = 'rgba(170,130,230,0.26)'
        g.fillRect(x0, top, 1, p.h)
        g.fillRect(x0, top, p.w, 1)
        if (p.cage) {
          g.fillStyle = 'rgba(210,210,220,0.26)'
          for (let k = -1; k <= p.w; k += 2) g.fillRect(x0 + k, top - 6, 1, 6)
          g.fillRect(x0 - 1, top - 6, p.w + 2, 1)
        }
        const a = 0.45 + 0.3 * Math.sin(this.t * 2 + p.ph)
        const lift = this.reduced?.matches ? 0 : Math.round(Math.sin(this.t * 1.2 + p.ph))
        this.prop(g, 'crystal', p.x - 3, top - 10 - lift, a)
      }
      for (let x = 0; x < LW; x++) {
        const hh = E.ground[x]
        g.fillStyle = 'rgba(225,215,160,0.20)'
        g.fillRect(x, LH - hh, 1, hh)
        g.fillStyle = 'rgba(245,240,200,0.30)'
        g.fillRect(x, LH - hh, 1, 1)
      }
      const mid = LW >> 1
      this.prop(g, 'portal', mid - 14, LH - E.ground[mid] - 7, 0.85)
      return
    }
    for (const isl of E.islands) {
      const b = this.bob(isl)
      isl.rows.forEach((half, k) => {
        g.fillStyle = k === 0 ? 'rgba(240,232,180,0.32)' : k < 3 ? 'rgba(215,205,155,0.22)' : 'rgba(150,125,175,0.16)'
        g.fillRect(isl.cx - half, isl.top + b + k, half * 2, 1)
      })
      for (const p of isl.props) {
        const [, , w, h] = PROP_BOX[p.name]
        this.prop(g, p.name, isl.cx + p.dx - (w >> 1), isl.top + b - h, 0.6)
      }
    }
  }

  draw(now) {
    const dt = this.last ? Math.min(0.2, (now - this.last) / 1000) : 0
    this.last = now
    const still = this.reduced?.matches
    if (!still) this.t += dt
    const cfg = SCENES[this.world]
    const { lctx: g, LW, LH } = this
    g.clearRect(0, 0, LW, LH)
    const sky = g.createLinearGradient(0, 0, 0, LH)
    sky.addColorStop(0, 'rgba(0,0,0,0)')
    sky.addColorStop(1, cfg.sky)
    g.fillStyle = sky
    g.fillRect(0, 0, LW, LH)
    if (cfg.lava) {
      const a = 0.16 + 0.06 * Math.sin(this.t * 1.3)
      const lava = g.createLinearGradient(0, LH * 0.7, 0, LH)
      lava.addColorStop(0, 'rgba(255,90,30,0)')
      lava.addColorStop(1, `rgba(255,110,40,${a.toFixed(3)})`)
      g.fillStyle = lava
      g.fillRect(0, LH * 0.7, LW, LH * 0.3)
    }
    if (this.end) this.drawEnd(g)
    this.layers.forEach(layer => {
      const off = Math.floor(this.t * layer.speed) % layer.L
      g.fillStyle = layer.color
      for (let x = 0; x < LW; x++) {
        const hh = layer.hts[(x + off) % layer.L]
        g.fillRect(x, LH - hh, 1, hh)
      }
      if (cfg.shape === 'peaks') {
        g.fillStyle = 'rgba(240,248,255,0.18)'
        for (let x = 0; x < LW; x++) g.fillRect(x, LH - layer.hts[(x + off) % layer.L], 1, 1)
      }
      for (const pr of layer.props) {
        const [, , w, h] = PROP_BOX[pr.name]
        let x = (pr.x - off + layer.L) % layer.L
        if (x > layer.L - w) x -= layer.L
        if (x > LW || x < -w) continue
        const hh = layer.hts[(pr.x + (w >> 1)) % layer.L]
        this.prop(g, pr.name, x, LH - hh - h + 1, 0.5)
      }
    })
    const [cr, cg, cb] = cfg.pc
    this.parts.forEach((p, i) => {
      if (!still) {
        p.x += (p.vx + (cfg.p === 'petal' ? Math.sin(this.t * 1.5 + p.ph) * 2 : 0)) * dt
        p.y += p.vy * dt
        if (cfg.p === 'ember') p.life -= dt * 0.25
        if (cfg.p === 'firefly') {
          p.vx = Math.max(-3, Math.min(3, p.vx + (this.rand() - 0.5) * dt * 4))
          p.vy = Math.max(-2, Math.min(2, p.vy + (this.rand() - 0.5) * dt * 4))
        }
        const out = p.y > LH + 2 || p.y < -2 || p.x < -4 || p.x > LW + 4 || p.life <= 0
        if (out) this.parts[i] = p.x < -4 && cfg.p !== 'firefly' ? Object.assign(this.particle(cfg.p, false), { x: LW + 2, y: this.rand() * LH }) : this.particle(cfg.p, false)
      }
      let a = 0.7
      if (cfg.p === 'firefly' || cfg.p === 'mote') a = 0.25 + 0.6 * Math.max(0, Math.sin(this.t * 2 + p.ph))
      if (cfg.p === 'ember') a = Math.max(0, p.life) * 0.95
      g.fillStyle = `rgba(${cr},${cg},${cb},${a.toFixed(3)})`
      g.fillRect(Math.round(p.x), Math.round(p.y), p.s, p.s)
    })
    const { ctx } = this
    ctx.imageSmoothingEnabled = false
    ctx.clearRect(0, 0, this.rect.w, this.rect.h)
    ctx.drawImage(this.low, 0, 0, LW, LH, 0, 0, LW * PX, LH * PX)
  }

  start() {
    const loop = now => {
      this.raf = requestAnimationFrame(loop)
      if (document.hidden || !this.visible) {
        this.last = 0
        return
      }
      if (now - this.last >= 66) {
        if (++this.frames % 30 === 0) this.place()
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

// ---- world change: a pixel-block wipe, then the next world --------------------------------
const WIPE_COLOR = { overworld: '#1d2a18', cherry: '#3a1f2c', snow: '#1c2433', nether: '#2a0e0c', end: '#160f22' }

export class Wipe {
  constructor() {
    this.canvas = document.createElement('canvas')
    this.canvas.id = 'hmt-wipe'
    Object.assign(this.canvas.style, { position: 'fixed', left: '0px', top: '0px', pointerEvents: 'none', zIndex: '60', display: 'none' })
    document.body.appendChild(this.canvas)
    this.ctx = this.canvas.getContext('2d')
    this.instant = false
    this.raf = 0
  }

  run(color, label, onCovered) {
    if (this.instant || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      onCovered()
      return Promise.resolve()
    }
    return new Promise(resolve => {
      const w = window.innerWidth
      const h = window.innerHeight
      const T = 48
      const cols = Math.ceil(w / T)
      const total = cols * Math.ceil(h / T)
      const order = Array.from({ length: total }, (_, i) => i)
      for (let i = total - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[order[i], order[j]] = [order[j], order[i]]
      }
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      Object.assign(this.canvas, { width: Math.round(w * dpr), height: Math.round(h * dpr) })
      Object.assign(this.canvas.style, { width: `${w}px`, height: `${h}px`, display: 'block' })
      const ctx = this.ctx
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      const font = getComputedStyle(document.documentElement).getPropertyValue('--mc-font').trim() || 'monospace'
      const COVER = 420
      const HOLD = 380
      const OPEN = 420
      let start = 0
      let covered = false
      const cover = () => {
        if (!covered) {
          covered = true
          try {
            onCovered()
          } catch {
            /* keep the wipe going */
          }
        }
      }
      const frame = now => {
        if (!start) start = now
        const t = now - start
        let k
        if (t < COVER) k = Math.floor((total * t) / COVER)
        else if (t < COVER + HOLD) {
          k = total
          cover()
        } else if (t < COVER + HOLD + OPEN) {
          cover()
          k = total - Math.floor((total * (t - COVER - HOLD)) / OPEN)
        } else {
          cover()
          ctx.clearRect(0, 0, w, h)
          this.canvas.style.display = 'none'
          resolve()
          return
        }
        ctx.clearRect(0, 0, w, h)
        for (let i = 0; i < k; i++) {
          const x = (order[i] % cols) * T
          const y = Math.floor(order[i] / cols) * T
          ctx.fillStyle = color
          ctx.fillRect(x, y, T, T)
          ctx.fillStyle = 'rgba(255,255,255,0.06)'
          ctx.fillRect(x, y, T, 3)
          ctx.fillStyle = 'rgba(0,0,0,0.25)'
          ctx.fillRect(x, y + T - 4, T, 4)
        }
        if (t >= COVER && t < COVER + HOLD + OPEN * 0.4) {
          ctx.font = `28px ${font}`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillStyle = 'rgba(0,0,0,0.6)'
          ctx.fillText(label, w / 2 + 3, h / 2 + 3)
          ctx.fillStyle = '#ffffff'
          ctx.fillText(label, w / 2, h / 2)
        }
        this.raf = requestAnimationFrame(frame)
      }
      this.raf = requestAnimationFrame(frame)
    })
  }

  destroy() {
    cancelAnimationFrame(this.raf)
    this.canvas.remove()
  }
}

// ---- auto world rotation (local to this desktop app; the skin you picked stays the base) ----
export class Rotator {
  constructor(storage, wipe, onWorld, now = () => Date.now()) {
    this.storage = storage
    this.wipe = wipe
    this.onWorld = onWorld
    this.now = now
    this.rand = Math.random
    this.enabled = storage?.get?.('autoWorld', true) !== false
    this.min = 4 * 60 * 1000
    this.max = 8 * 60 * 1000
    this.base = ''
    this.world = ''
    this.due = 0
    this.bag = []
    this.busy = false
  }

  baseWorld() {
    return getComputedStyle(document.documentElement).getPropertyValue('--mc-skin-world').trim().replace(/"/g, '')
  }

  schedule() {
    this.due = this.now() + this.min + this.rand() * (this.max - this.min)
  }

  tick() {
    const root = document.documentElement
    if (root.dataset.mcTheme !== '1') {
      delete root.dataset.mcRot
      this.base = ''
      return
    }
    const base = this.baseWorld()
    if (!base || !WORLD_INFO[base]) return
    if (base !== this.base) {
      // you picked a (new) minecraft skin: show it as-is and start counting again
      this.base = base
      this.world = base
      this.bag = []
      delete root.dataset.mcRot
      this.schedule()
      this.onWorld()
      return
    }
    if (document.hidden) {
      if (this.now() >= this.due) this.schedule()
      return
    }
    if (this.enabled && !this.busy && this.now() >= this.due) this.go()
  }

  pickNext() {
    if (!this.bag.length) {
      this.bag = Object.keys(WORLD_INFO).filter(k => k !== this.world)
      for (let i = this.bag.length - 1; i > 0; i--) {
        const j = Math.floor(this.rand() * (i + 1))
        ;[this.bag[i], this.bag[j]] = [this.bag[j], this.bag[i]]
      }
    }
    return this.bag.pop()
  }

  apply(w) {
    const root = document.documentElement
    if (w === this.base) delete root.dataset.mcRot
    else root.dataset.mcRot = w
    this.world = w
    this.onWorld()
  }

  async go(target) {
    if (this.busy) return
    const next = target || this.pickNext()
    if (!next) return
    this.busy = true
    try {
      await this.wipe.run(WIPE_COLOR[next] || '#111', WORLD_INFO[next].label, () => this.apply(next))
    } finally {
      this.busy = false
      this.schedule()
    }
  }

  setEnabled(on) {
    this.enabled = on
    this.storage?.set?.('autoWorld', on)
    this.schedule()
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
    for (const id of ['hmt-critters', 'hmt-scene', 'hmt-wipe', 'hmt-world-css']) document.getElementById(id)?.remove()
    const worldStyle = document.createElement('style')
    worldStyle.id = 'hmt-world-css'
    worldStyle.textContent = WORLD_CSS
    document.head.appendChild(worldStyle)
    const critters = new Critters()
    const scene = new Scene(undefined, () => critters.endMode)
    critters.perches = () => scene.perches()
    const wipe = new Wipe()
    const rot = new Rotator(ctx.storage, wipe, () => {
      critters.place()
      scene.place()
    })
    window.__hmt = { critters, scene, wipe, rot }
    window.__hmtCritters = critters
    critters.place()
    critters.start()
    scene.place()
    scene.start()
    rot.tick()
    const tick = setInterval(() => {
      detectTheme()
      refresh()
      rot.tick()
      critters.place()
      scene.place()
    }, 2000)
    const placeOnResize = () => {
      critters.place()
      scene.place()
    }
    window.addEventListener('resize', placeOnResize)
    ctx.register({
      id: 'auto-world',
      area: PALETTE_AREA,
      data: {
        id: `${ID}.auto-world`,
        label: 'Minecraft：自動換世界（開／關）',
        keywords: ['minecraft', 'world', '世界', 'auto', '輪替'],
        detail: () => (rot.enabled ? '開' : '關'),
        detailVariant: 'state',
        run: () => rot.setEnabled(!rot.enabled)
      }
    })
    ctx.register({
      id: 'next-world',
      area: PALETTE_AREA,
      data: {
        id: `${ID}.next-world`,
        label: 'Minecraft：現在換一個世界',
        keywords: ['minecraft', 'world', '世界', 'next', '換'],
        run: () => rot.go()
      }
    })
    const subscribe = ctx.onEvent || host.onEvent
    const unsubscribe = subscribe('*', onEvent)
    ctx.register({ id: 'chip', area: STATUSBAR_AREAS.right, order: 50, render: () => jsx(ActivityChip, {}) })
    ctx.onDispose?.(() => {
      clearInterval(tick)
      window.removeEventListener('resize', placeOnResize)
      critters.destroy()
      scene.destroy()
      wipe.destroy()
      worldStyle.remove()
      delete document.documentElement.dataset.mcRot
      clearTimeout(flashTimer)
      if (typeof unsubscribe === 'function') unsubscribe()
      style.remove()
      delete document.documentElement.dataset.mcActivity
      delete document.documentElement.dataset.mcTheme
    })
  }
}
