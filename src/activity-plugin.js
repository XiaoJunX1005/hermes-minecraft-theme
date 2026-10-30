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
  blaze:   { size: 32, speed: 28, turn: 1.2, wander: 0.5, pause: [1.2, 3.5], pauseChance: 0.7, bob: 5, fps: 9, turns: false, max: 2, calm: true },
  cod:     { size: 32, speed: 40, turn: 1.8, wander: 0.8, pause: [0.6, 1.6], pauseChance: 0.3, bob: 1, fps: 10, turns: true, max: 3, mode: 'swim' },
  salmon:  { size: 32, speed: 52, turn: 1.6, wander: 0.7, pause: [0.4, 1.2], pauseChance: 0.2, bob: 1, fps: 12, turns: true, max: 2, mode: 'swim' },
  tropical:{ size: 32, speed: 34, turn: 2.6, wander: 1.2, pause: [0.5, 1.5], pauseChance: 0.45, bob: 1, fps: 12, turns: true, max: 4, mode: 'swim' },
  squid:   { size: 32, speed: 20, turn: 0.8, wander: 0.4, pause: [1, 3], pauseChance: 0.5, bob: 4, fps: 6, turns: false, max: 1, mode: 'swim', calm: true },
  glowsquid:{ size: 32, speed: 20, turn: 0.8, wander: 0.4, pause: [1, 3], pauseChance: 0.5, bob: 4, fps: 6, turns: false, max: 1, mode: 'swim', calm: true },
  axolotl: { size: 32, speed: 22, turn: 0, wander: 0, pause: [1, 3], pauseChance: 0.6, bob: 0, fps: 8, turns: true, max: 2, mode: 'pool' },
  rabbit:  { size: 32, speed: 55, turn: 0, wander: 0, pause: [0.6, 2], pauseChance: 0.7, bob: 0, fps: 10, turns: true, max: 3, mode: 'ground', hop: true },
  camel:   { size: 48, speed: 18, turn: 0, wander: 0, pause: [2, 5], pauseChance: 0.5, bob: 0, fps: 5, turns: true, max: 1, mode: 'ground', calm: true },
  mooshroom:{ size: 32, speed: 16, turn: 0, wander: 0, pause: [2, 5], pauseChance: 0.6, bob: 0, fps: 6, turns: true, max: 3, mode: 'ground', calm: true },
  warden:  { size: 48, speed: 10, turn: 0, wander: 0, pause: [3, 7], pauseChance: 0.7, bob: 0, fps: 4, turns: true, max: 1, mode: 'ground', calm: true }
}
const POOLS = {
  overworld: { n: [2, 5], pick: [['bee', 5], ['bee-pollen', 3], ['bee-angry', 1], ['allay', 2], ['parrot-red', 1], ['parrot-blue', 1], ['parrot-green', 1]] },
  cherry: { n: [2, 5], pick: [['bee', 4], ['bee-pollen', 4], ['allay', 2], ['parrot-cyan', 1], ['parrot-gray', 1]] },
  snow: { n: [2, 4], pick: [['allay', 3], ['bat', 2], ['phantom', 1]] },
  nether: { n: [2, 4], pick: [['ghast', 1], ['blaze', 3]] },
  end: { n: [2, 3], pick: [['phantom', 2], ['dragon', 1]] },
  ocean: { n: [3, 6], pick: [['cod', 4], ['salmon', 3], ['tropical-orange', 2], ['tropical-yellow', 2], ['tropical-blue', 2], ['squid', 1], ['glowsquid', 1]] },
  lush: { n: [2, 4], pick: [['axolotl-pink', 3], ['axolotl-blue', 1], ['bat', 2]] },
  desert: { n: [2, 4], pick: [['rabbit-gold', 3], ['rabbit-brown', 2], ['camel', 1]] },
  mushroom: { n: [2, 3], pick: [['mooshroom-red', 4], ['mooshroom-brown', 1]] },
  deepdark: { n: [1, 2], pick: [['warden', 1], ['bat', 2]] }
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
    this.onLeave = () => {
      this.pointer.x = -1e4
      this.pointer.y = -1e4
    }
    this.fx = []
    this.stings = 0
    window.addEventListener('pointermove', this.onMove, { passive: true })
    document.documentElement.addEventListener('pointerleave', this.onLeave)
    window.addEventListener('blur', this.onLeave)
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
    if (S.mode === 'ground') {
      c.y = this.floorY(c)
      if (fromEdge) c.x = this.rand() < 0.5 ? -30 : this.w + 30
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
      if (SPECIES[c.sp].mode === 'ground') c.tx = c.x < this.w / 2 ? -120 : this.w + 120
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
        const any = ps.map((p, i) => ({ p, i })).filter(({ i }) => !used.has(i) && i !== c.perch)
        const other = any.filter(({ p }) => p.isl !== ps[c.perch].isl)
        const opts = other.length ? other : any
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
    if (S.mode === 'ground') return this.stepGround(c, dt, boost)
    if (S.mode === 'pool') return this.stepPool(c, dt, boost)
    if (c.sp === 'bee' && this.beeMind(c, dt)) return
    const flying = c.state === 'fly'
    let target = Math.atan2(c.ty - c.y, c.tx - c.x)
    if (S.mode === 'swim') {
      const dx = c.tx - c.x
      target = Math.atan2(Math.max(-0.35 * Math.abs(dx), Math.min(0.35 * Math.abs(dx), c.ty - c.y)), dx)
    }
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
    this.turnUpdate(c, dt, Math.cos(c.h) * c.spd)
  }

  turnUpdate(c, dt, vx) {
    const S = SPECIES[c.sp]
    if (c.turnT >= 0) {
      c.turnT += dt
      if (c.turnT >= TURN) {
        c.face = c.nextFace
        c.turnT = -1
        c.lastTurn = this.t
      }
    } else if (S.turns) {
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

  /** Bees: harass one (come close, back off, three times within 8 s) and it gets angry,
   *  shakes for half a second, charges the cursor, bounces off, flees, then calms down. */
  beeMind(c, dt) {
    if (c.state !== 'fly' || this.reduced?.matches) return false
    const P = this.pointer
    const live = P.x > -1000
    const d = live ? Math.hypot(c.x - P.x, c.y - P.y) : 1e9
    if (!c.mood || c.mood === 'calm') {
      c.mood = 'calm'
      if (!c.near && d < 80) {
        c.near = true
        ;(c.pokes = c.pokes || []).push(this.t)
      } else if (c.near && d > 130) {
        c.near = false
      }
      c.pokes = (c.pokes || []).filter(t => this.t - t < 8)
      const busyBee = this.list.some(o => o !== c && o.mood && o.mood !== 'calm')
      if (c.pokes.length >= 3 && this.t >= (c.coolUntil || 0) && !busyBee) {
        c.mood = 'warn'
        c.moodT = 0
        c.pokes = []
        c.v0 = c.v
        c.v = 'bee-angry'
        c.wait = 0
      }
      if (c.mood === 'calm') return false
    }
    c.moodT += dt
    if (c.mood === 'warn') {
      c.spd = 0
      c.jx = Math.round((this.rand() - 0.5) * 4)
      if (c.moodT > 0.5) {
        c.mood = 'charge'
        c.moodT = 0
        c.jx = 0
      }
    } else if (c.mood === 'charge') {
      if (!live || c.moodT > 2) {
        this.beeFlee(c)
      } else {
        const want = Math.atan2(P.y - c.y, P.x - c.x)
        const da = Math.atan2(Math.sin(want - c.h), Math.cos(want - c.h))
        c.h += Math.max(-7 * dt, Math.min(7 * dt, da))
        c.spd += (280 - c.spd) * Math.min(1, dt * 4)
        if (d < 16) {
          this.burst(c.x + Math.cos(c.h) * 8, c.y + Math.sin(c.h) * 8)
          this.stings++
          c.h += Math.PI
          c.spd = 170
          c.mood = 'bounce'
          c.moodT = 0
        }
      }
    } else if (c.mood === 'bounce') {
      c.spd *= Math.max(0, 1 - dt * 5)
      if (c.moodT > 0.3) this.beeFlee(c)
    } else if (c.mood === 'flee') {
      c.spd += (SPECIES.bee.speed * 3.2 - c.spd) * Math.min(1, dt * 3)
      if (c.moodT > 1.5) {
        c.mood = 'calm'
        c.v = c.v0 || c.v
        c.coolUntil = this.t + 15
        c.near = d < 80
        this.retarget(c)
      }
    }
    if (c.mood !== 'warn') {
      c.x += Math.cos(c.h) * c.spd * dt
      c.y += Math.sin(c.h) * c.spd * dt
      const r = SPECIES.bee.size / 2
      if (c.x < r || c.x > this.w - r) {
        c.x = Math.min(this.w - r, Math.max(r, c.x))
        c.h = Math.PI - c.h
      }
      if (c.y < r || c.y > this.h - r) {
        c.y = Math.min(this.h - r, Math.max(r, c.y))
        c.h = -c.h
      }
    }
    this.turnUpdate(c, dt, Math.cos(c.h) * c.spd)
    return true
  }

  beeFlee(c) {
    const P = this.pointer
    c.mood = 'flee'
    c.moodT = 0
    if (P.x > -1000) c.h = Math.atan2(c.y - P.y, c.x - P.x)
  }

  burst(x, y) {
    for (let k = 0; k < 8; k++) {
      const a = (k / 8) * Math.PI * 2
      this.fx.push({ x, y, vx: Math.cos(a) * 70, vy: Math.sin(a) * 70 - 20, life: 0.45 })
    }
  }

  /** Any angry bee calms down (window hidden, theme switched off, ...). */
  calmAll() {
    for (const c of this.list) {
      if (c.mood && c.mood !== 'calm') {
        c.mood = 'calm'
        c.v = c.v0 || c.v
        c.jx = 0
        c.coolUntil = this.t + 15
      }
      c.pokes = []
      c.near = false
    }
  }

  /** Axolotls live in the lush-cave pools: swim, rest, now and then climb out and walk along the
   *  bank for a few seconds, then slip back in. A cursor nearby always sends them back into the water. */
  stepPool(c, dt, boost) {
    const S = SPECIES[c.sp]
    if (c.state === 'leave') {
      c.x = -999
      return
    }
    const ps = this.pools ? this.pools() : []
    if (!ps.length) return this.stepGround(c, dt, boost)
    if (c.pool == null || c.pool >= ps.length) {
      const used = new Set(this.list.filter(o => o !== c && o.pool != null).map(o => o.pool))
      const free = ps.map((_, i) => i).filter(i => !used.has(i))
      c.pool = free.length ? free[Math.floor(this.rand() * free.length)] : Math.floor(this.rand() * ps.length)
      c.x = (ps[c.pool].x0 + ps[c.pool].x1) / 2
      c.tx = c.x
      c.land = false
      c.home = false
      c.state = 'fly'
    }
    const P = ps[c.pool]
    const r = S.size * 0.4
    const lo = P.x0 + r
    const hi = Math.max(lo, P.x1 - r)
    const blo = P.bank0 + r
    const bhi = Math.max(blo, P.bank1 - r)
    const swimY = P.top + (P.bottom - P.top) * 0.45
    const landY = P.top - S.size / 2 + 3
    const near = dt > 0 && Math.abs(c.x - this.pointer.x) < 70 && Math.abs(c.y - this.pointer.y) < 60
    let want = S.speed * boost
    if (c.wait > 0) {
      c.wait -= dt
      want = 0
    }
    if (c.land) {
      c.landT -= dt
      if (!c.home && (near || c.landT <= 0)) {
        c.home = true
        c.tx = (lo + hi) / 2 + (this.rand() - 0.5) * (hi - lo) * 0.5
      }
      if (near) {
        want = S.speed * 2.6
        c.wait = 0
      }
      if (c.home && c.x >= lo && c.x <= hi) {
        c.land = false
        c.home = false
        c.tx = lo + this.rand() * (hi - lo)
      }
    } else {
      if (near) {
        c.tx = c.x - lo > hi - c.x ? lo : hi
        want = S.speed * 2.5
        c.wait = 0
      } else if (dt > 0 && c.wait <= 0 && this.rand() < dt * 0.08 && bhi - blo > hi - lo + 20) {
        const left = P.x0 - blo
        const right = bhi - P.x1
        c.land = true
        c.home = false
        c.landT = 3 + this.rand() * 4
        c.tx = right > 8 && (left <= 8 || this.rand() < 0.5) ? P.x1 + 4 + this.rand() * (right - 4) : blo + this.rand() * Math.max(1, left - 4)
      }
      if (!c.land && (c.tx < lo || c.tx > hi)) c.tx = lo + this.rand() * (hi - lo)
    }
    const dir = Math.sign(c.tx - c.x) || c.face
    if (c.turnT >= 0) want = 0
    c.spd += (want - c.spd) * Math.min(1, dt * 3)
    if (c.turnT < 0 && dir === c.face) c.x += dir * c.spd * dt
    c.x = Math.min(c.land ? bhi : hi, Math.max(c.land ? blo : lo, c.x))
    const ashore = c.x < P.x0 || c.x > P.x1
    const ty = ashore ? landY : swimY + (dt ? Math.sin(this.t * 1.6 + c.phase) * 1.5 : 0)
    c.y = dt > 0 && c.y > -500 ? c.y + (ty - c.y) * Math.min(1, dt * 6) : ty
    c.h = dir > 0 ? 0 : Math.PI
    if (dt > 0 && Math.abs(c.tx - c.x) < 4) {
      if (c.land && !c.home) {
        c.wait = 0.6 + this.rand() * 1.5
        c.tx = c.x > P.x1 ? P.x1 + 4 + this.rand() * Math.max(1, bhi - P.x1 - 4) : blo + this.rand() * Math.max(1, P.x0 - blo - 4)
      } else if (!c.land) {
        c.tx = lo + this.rand() * (hi - lo)
        if (this.rand() < S.pauseChance) c.wait = S.pause[0] + this.rand() * (S.pause[1] - S.pause[0])
      }
    }
    c.idle = c.wait > 0 && c.spd < 6 ? c.idle + dt : 0
    this.turnUpdate(c, dt, dir * Math.max(c.spd, 10))
  }

  /** Ground level: just above the status bar (the grass strip the pet walks on). */
  floorY(c) {
    const bar = document.querySelector('[data-slot="statusbar"]')
    const top = bar ? bar.getBoundingClientRect().top : this.h
    return Math.min(this.h, top) - SPECIES[c.sp].size / 2 + 2
  }

  /** Walkers stay on the floor: stroll to a spot, pause, maybe turn back; step aside from the cursor. */
  stepGround(c, dt, boost) {
    const S = SPECIES[c.sp]
    c.y = this.floorY(c)
    const flying = c.state === 'fly'
    let want = S.speed * boost * (c.state === 'leave' ? 1.6 : 1)
    if (flying && c.wait > 0) {
      c.wait -= dt
      want = 0
    }
    let dir = Math.sign(c.tx - c.x) || c.face
    if (flying && Math.abs(c.x - this.pointer.x) < 90 && Math.abs(c.y - this.pointer.y) < 70) {
      dir = c.x >= this.pointer.x ? 1 : -1
      want = S.speed * (S.calm ? 1.4 : 2.4)
      c.wait = 0
      c.tx = Math.max(40, Math.min(this.w - 40, c.x + dir * 220))
    }
    if (c.turnT >= 0) want = 0
    c.spd += (want - c.spd) * Math.min(1, dt * 3)
    if (!S.turns) c.face = dir
    if (c.turnT < 0 && dir === c.face) c.x += dir * c.spd * dt
    c.h = dir > 0 ? 0 : Math.PI
    if (flying) {
      if (Math.abs(c.tx - c.x) < 10) {
        this.retarget(c)
        if (this.rand() < S.pauseChance) c.wait = (S.pause[0] + this.rand() * (S.pause[1] - S.pause[0])) / boost
      }
      const r = S.size / 2
      c.x = Math.min(this.w - r, Math.max(r, c.x))
    } else if (c.state === 'enter' && c.x > 40 && c.x < this.w - 40) {
      c.state = 'fly'
    }
    c.hopP = S.hop && c.spd > 5 ? (c.hopP || 0) + dt * 3.2 : 0
    c.idle = c.wait > 0 && c.spd < 6 ? c.idle + dt : 0
    this.turnUpdate(c, dt, dir * Math.max(c.spd, 10))
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
      else if (SPECIES[c.sp].mode === 'pool') this.stepPool(c, still ? 0 : dt, boost)
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
      if (c.x < -500) continue
      const bob = still ? 0 : Math.sin(this.t * 2.4 + c.phase) * S.bob - Math.sin(this.hop * Math.PI) * 16 - (S.hop && c.hopP ? Math.abs(Math.sin(c.hopP * Math.PI)) * 7 : 0)
      const hasFront = CRITTER_ROWS.includes(`${c.v}:front`)
      let view = 'front'
      let sx = 1
      let face = c.face
      if (S.turns) {
        view = 'side'
        if (c.turnT >= 0) {
          const p = c.turnT / TURN
          if (!hasFront) {
            // no front view: squeeze, swap sides at the midpoint, unsqueeze
            if (p < 0.5) sx = 1 - p * 1.3
            else {
              face = c.nextFace
              sx = 0.35 + (p - 0.5) * 1.3
            }
          } else if (p < 1 / 3) sx = 1 - p * 3 * 0.65
          else if (p < 2 / 3) view = 'front'
          else {
            face = c.nextFace
            sx = 0.35 + (p - 2 / 3) * 3 * 0.65
          }
        } else if (c.idle > 0.8 && hasFront) {
          view = 'front'
        }
      }
      const row = CRITTER_ROWS.indexOf(`${c.v}:${view}`)
      if (row < 0) continue
      const f = still ? 0 : Math.floor(this.t * S.fps + c.phase * 3) % 8
      ctx.save()
      ctx.translate(Math.round(c.x + (c.jx || 0)), Math.round(c.y + bob))
      if (view === 'side') ctx.scale(face * sx, 1)
      ctx.drawImage(this.atlas, f * 16, row * 16, 16, 16, -S.size / 2, -S.size / 2, S.size, S.size)
      ctx.restore()
    }
    this.fx = this.fx.filter(p => (p.life -= dt) > 0)
    ctx.fillStyle = 'rgba(255,230,120,0.9)'
    for (const p of this.fx) {
      p.x += p.vx * dt
      p.y += p.vy * dt
      p.vy += 120 * dt
      ctx.fillRect(Math.round(p.x), Math.round(p.y), 3, 3)
    }
  }

  start() {
    const loop = now => {
      this.raf = requestAnimationFrame(loop)
      if (document.hidden || !this.visible) {
        this.last = 0
        this.calmAll()
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
    document.documentElement.removeEventListener('pointerleave', this.onLeave)
    window.removeEventListener('blur', this.onLeave)
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
  end: { sky: 'rgba(130,80,190,0.18)', end: true, layers: [], p: 'mote', n: 26, pc: [200, 150, 255] },
  ocean: { sky: 'rgba(40,120,170,0.2)', shape: 'hills', rays: true, layers: [['rgba(60,110,130,0.18)', 0.12, 1], ['rgba(120,150,120,0.2)', 0.08, 2.5]],
    props: [['kelp', 4], ['seagrass', 3], ['coral', 3]], p: 'bubble', n: 30, pc: [190, 235, 255] },
  lush: { sky: 'rgba(90,150,80,0.14)', shape: 'hills', pools: 2, ceil: { color: 'rgba(80,110,90,0.2)', frac: 0.12, props: [['vine', 3], ['berryvine', 2]] },
    layers: [['rgba(80,130,70,0.18)', 0.10, 0.4], ['rgba(110,160,80,0.22)', 0.09, 0]], props: [['azalea', 3], ['dripleaf', 2]], p: 'spore', n: 22, pc: [255, 190, 230] },
  desert: { sky: 'rgba(230,180,100,0.18)', shape: 'hills', layers: [['rgba(200,160,100,0.18)', 0.14, 1], ['rgba(230,200,130,0.22)', 0.09, 2.5]],
    props: [['cactus', 4], ['deadbush', 3], ['temple', 1]], p: 'sand', n: 34, pc: [255, 225, 160] },
  mushroom: { sky: 'rgba(170,110,180,0.16)', shape: 'hills', layers: [['rgba(120,90,140,0.18)', 0.14, 1], ['rgba(150,120,170,0.22)', 0.09, 2.5]],
    props: [['redshroom', 3], ['brownshroom', 2]], p: 'spore', n: 20, pc: [220, 200, 255] },
  deepdark: { sky: 'rgba(20,90,110,0.16)', shape: 'hills', pulse: true, layers: [['rgba(40,80,100,0.16)', 0.18, 0.6], ['rgba(30,110,130,0.2)', 0.08, 1.5]],
    props: [['sensor', 4], ['shrieker', 2], ['citywall', 1]], p: 'sculk', n: 22, pc: [90, 240, 250] }
}
// Three layouts per world; one is picked each time you enter it (stable until you leave).
const VARIANTS = {
  overworld: [
    { name: 'meadow', props: [['flowers', 4], ['oak', 1], ['birch', 1]], gap: [18, 60] },
    { name: 'forest', props: [['oak', 3], ['oak2', 3], ['oak3', 2], ['birch', 1]], gap: [3, 16], backProps: [['oak3', 2], ['oak', 1]] },
    { name: 'birch', props: [['birch', 3], ['birch2', 3], ['flowers', 2]], gap: [8, 30], backProps: [['birch2', 1]] }
  ],
  cherry: [
    { name: 'slope', props: [['cherry', 2], ['cherry3', 1], ['flowers', 3]], gap: [20, 60] },
    { name: 'grove', props: [['cherry', 3], ['cherry2', 3], ['cherry3', 2]], gap: [2, 14], backProps: [['cherry2', 2]] },
    { name: 'pond', pools: 1, layers: [['rgba(150,80,120,0.16)', 0.16, 0.6], ['rgba(190,110,150,0.2)', 0.10, 0]],
      props: [['cherry3', 2], ['cherry', 2], ['flowers', 2]], gap: [10, 40] }
  ],
  snow: [
    { name: 'taiga', props: [['spruce', 3], ['spruce2', 3], ['spruce3', 2]], gap: [3, 16], backProps: [['spruce2', 2]] },
    { name: 'tundra', shape: 'hills', layers: [['rgba(110,130,180,0.14)', 0.10, 1], ['rgba(160,180,220,0.2)', 0.07, 2.5]],
      props: [['igloo', 1], ['spruce3', 2]], gap: [40, 110] },
    { name: 'peaks', layers: [['rgba(110,130,180,0.18)', 0.30, 0.8], ['rgba(160,180,220,0.22)', 0.16, 2]], props: [['spruce3', 2], ['spruce', 1]], gap: [30, 80] }
  ],
  nether: [
    { name: 'crimson', props: [['crimson', 3], ['crimson2', 3], ['crimson3', 2]], gap: [4, 20], p: 'spore', pc: [255, 90, 90], n: 30 },
    { name: 'warped', sky: 'rgba(40,140,130,0.18)', props: [['warped', 3], ['warped2', 3], ['warped3', 2]], gap: [4, 20], p: 'spore', pc: [90, 230, 210], n: 30 },
    { name: 'basalt', props: [], p: 'ash', pc: [190, 190, 196], n: 55, layers: [['rgba(90,80,90,0.2)', 0.28, 1], ['rgba(120,100,100,0.22)', 0.16, 2.5]] }
  ],
  ocean: [
    { name: 'kelp', sky: 'rgba(20,110,70,0.3)', props: [['kelp3', 4], ['kelp', 3], ['kelp2', 1]], gap: [1, 8], backProps: [['kelp3', 3], ['kelp', 2]],
      layers: [['rgba(30,90,60,0.22)', 0.16, 0.8], ['rgba(50,110,70,0.24)', 0.09, 2]] },
    { name: 'reef', sky: 'rgba(60,210,230,0.34)', rays: true, props: [['reef', 3], ['coral', 3], ['coral2', 3], ['seagrass', 1]], gap: [0, 10], n: 40,
      layers: [['rgba(70,170,170,0.16)', 0.10, 1], ['rgba(150,170,130,0.2)', 0.06, 2.5]] },
    { name: 'sand', sky: 'rgba(110,160,170,0.16)', props: [['seagrass', 3], ['seagrass2', 1]], gap: [60, 150], n: 18,
      layers: [['rgba(150,150,120,0.14)', 0.10, 1], ['rgba(225,205,145,0.24)', 0.13, 2.5]] }
  ],
  lush: [
    { name: 'pools', props: [['azalea', 1], ['dripleaf', 1]], gap: [30, 80] },
    { name: 'dripleaf', pools: 1, poolAt: [0.5], poolW: 50, sky: 'rgba(60,160,150,0.16)', props: [['dripleaf', 5], ['azalea', 1]], gap: [1, 8], backProps: [['dripleaf', 2]],
      ceil: { color: 'rgba(70,110,100,0.22)', frac: 0.10, props: [['vine', 1]] } },
    { name: 'azalea', pools: 1, poolAt: [0.84], poolW: 26, sky: 'rgba(150,140,90,0.16)', props: [['azalea2', 3], ['azalea', 2]], gap: [2, 12], backProps: [['azalea2', 2]],
      ceil: { color: 'rgba(90,100,70,0.24)', frac: 0.2, props: [['berryvine', 1]] }, n: 34 }
  ],
  desert: [
    { name: 'dunes', props: [['cactus', 3], ['cactus2', 2], ['deadbush', 3]], gap: [14, 50] },
    { name: 'temple', props: [['temple', 1], ['cactus3', 2], ['deadbush', 2]], gap: [30, 80] },
    { name: 'flats', layers: [['rgba(200,160,100,0.14)', 0.07, 1], ['rgba(230,200,130,0.2)', 0.05, 2.5]], props: [['deadbush', 4], ['cactus3', 1]], gap: [24, 70] }
  ],
  mushroom: [
    { name: 'forest', props: [['redshroom', 3], ['redshroom2', 2], ['brownshroom', 2], ['brownshroom2', 1]], gap: [2, 14], backProps: [['redshroom2', 1]] },
    { name: 'fields', props: [['redshroom', 1], ['brownshroom', 1], ['brownshroom2', 1]], gap: [40, 100] },
    { name: 'brown', props: [['brownshroom2', 3], ['brownshroom', 2], ['redshroom2', 1]], gap: [6, 26] }
  ],
  deepdark: [
    { name: 'city', sky: 'rgba(90,100,140,0.2)', p: 'mote', pc: [150, 170, 210], props: [['citywall', 3], ['ruin', 2], ['sensor', 1]], gap: [0, 12], backProps: [['ruin', 2], ['citywall', 1]], ceil: null },
    { name: 'sculk', shape: 'flat', sky: 'rgba(20,170,180,0.26)', layers: [['rgba(20,120,130,0.2)', 0.10, 0.6], ['rgba(30,150,160,0.26)', 0.07, 1.5]], props: [['sensor', 4], ['shrieker', 3]], gap: [2, 12], n: 44, ceil: null },
    { name: 'cave', sky: 'rgba(110,80,50,0.16)', p: 'mote', pc: [220, 190, 150], props: [['sensor', 1]], gap: [60, 140], ceil: { color: 'rgba(40,60,70,0.24)', frac: 0.2, props: [['dripstone', 1]] },
      layers: [['rgba(40,80,100,0.18)', 0.32, 0.6], ['rgba(30,110,130,0.2)', 0.14, 1.5]] }
  ]
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
    // Second canvas with normal blending: only the End's obsidian pillars go here, so they can be dark.
    this.solid = document.createElement('canvas')
    this.solid.id = 'hmt-scene-solid'
    Object.assign(this.solid.style, { position: 'fixed', pointerEvents: 'none', zIndex: '2', imageRendering: 'pixelated', display: 'none', opacity: '0.68' })
    document.body.appendChild(this.solid)
    this.slow = document.createElement('canvas')
    this.sctx = this.slow.getContext('2d')
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
    this.solid.style.display = this.visible ? 'block' : 'none'
    if (!this.visible) return false
    const w = Math.round(r.width)
    const h = Math.round(r.height)
    const resized = w !== this.rect.w || h !== this.rect.h
    if (resized || r.left !== this.rect.x || r.top !== this.rect.y) {
      this.rect = { x: r.left, y: r.top, w, h }
      for (const c of [this.canvas, this.solid]) {
        Object.assign(c.style, { left: `${r.left}px`, top: `${r.top}px`, width: `${w}px`, height: `${h}px` })
        c.width = w
        c.height = h
      }
    }
    const world = SCENES[worldOf()] ? worldOf() : 'overworld'
    const mode = world === 'end' ? this.getMode() || 'main' : ''
    if (world !== this.world || mode !== this.mode) this.vi = null
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
      } else if (shape === 'flat') {
        v = 0.42 + 0.05 * Math.sin(2 * Math.PI * (3 * u + i * 0.3))
      } else {
        v = 0.6 + 0.25 * Math.sin(2 * Math.PI * (2 * u + i * 0.3)) + 0.15 * Math.sin(2 * Math.PI * (5 * u + i))
      }
      out[x] = Math.round((base * v) / 2) * 2
    }
    for (let x = 0; x < L; x++) out[x] = out[x - (x % 3)]
    return out
  }

  build() {
    const vs = VARIANTS[this.world] || []
    if (this.vi == null || this.vi >= vs.length) this.vi = vs.length ? Math.floor(this.rand() * vs.length) : -1
    const cfg = (this.cfg = vs.length ? Object.assign({}, SCENES[this.world], vs[this.vi]) : SCENES[this.world])
    const LW = Math.max(1, Math.ceil(this.rect.w / PX))
    const LH = Math.max(1, Math.ceil(this.rect.h / PX))
    this.low.width = LW
    this.low.height = LH
    this.slow.width = LW
    this.slow.height = LH
    this.LW = LW
    this.LH = LH
    const L = LW * 2
    this.layers = cfg.layers.map(([color, frac, speed], i) => ({ color, speed, L, hts: this.heights(cfg.shape, L, LH * frac, i), props: [] }))
    const front = this.layers[this.layers.length - 1]
    const scatter = (layer, list, gap) => {
      if (!layer || !list || !list.length) return
      const total = list.reduce((a, [, w]) => a + w, 0)
      let x = 10 + this.rand() * 20
      while (x < L - 30) {
        let r = this.rand() * total
        let name = list[0][0]
        for (const [n, w] of list) {
          if ((r -= w) <= 0) {
            name = n
            break
          }
        }
        layer.props.push({ name, x: Math.round(x), flip: this.rand() < 0.5 })
        x += PROP_BOX[name][2] + gap[0] + this.rand() * (gap[1] - gap[0])
      }
    }
    scatter(front, cfg.props, cfg.gap || [12, 57])
    if (this.layers.length > 1) scatter(this.layers[0], cfg.backProps, [20, 70])
    this.ceil = null
    if (cfg.ceil) {
      const C = { color: cfg.ceil.color, speed: front ? front.speed : 2, L, hts: this.heights('hills', L, LH * cfg.ceil.frac, 5), props: [] }
      const total = cfg.ceil.props.reduce((a, [, w]) => a + w, 0)
      let x = cfg.ceil.props.length ? 6 : L
      while (x < L - 10) {
        let r = this.rand() * total
        let name = cfg.ceil.props[0][0]
        for (const [n, w] of cfg.ceil.props) {
          if ((r -= w) <= 0) {
            name = n
            break
          }
        }
        C.props.push({ name, x: Math.round(x) })
        x += PROP_BOX[name][2] + 6 + this.rand() * 30
      }
      this.ceil = C
    }
    this.end = cfg.end ? this.buildEnd() : null
    this.poolList = []
    if (cfg.pools && front) {
      for (const u of (cfg.poolAt || [0.24, 0.74]).slice(0, cfg.pools)) {
        const w = cfg.poolW || 34
        const d = 8
        const x0 = Math.max(2, Math.min(LW - w - 2, Math.round(u * LW - w / 2)))
        let hb = 12
        for (let x = x0; x < x0 + w; x++) hb = Math.max(hb, front.hts[x])
        const b = 14
        for (let x = Math.max(0, x0 - b); x < Math.min(LW, x0 + w + b); x++) front.hts[x] = hb
        for (let x = x0; x < x0 + w; x++) front.hts[x] = hb - d
        front.props = front.props.filter(p => p.x + PROP_BOX[p.name][2] < x0 - b - 2 || p.x > x0 + w + b + 2)
        this.poolList.push({ x0, w, hb, d, b })
      }
    }
    this.parts = Array.from({ length: cfg.n }, () => this.particle(cfg.p, true))
  }

  /** End: 'main' = the main island (obsidian pillars, crystals, exit portal); 'outer' = outer islands (chorus, End city). */
  buildEnd() {
    const { LW, LH } = this
    const r = this.rand
    if (this.mode === 'main') {
      const ground = Array.from({ length: LW }, (_, x) =>
        Math.round(LH * (0.09 + 0.03 * Math.sin((x / LW) * Math.PI * 3) + 0.015 * Math.sin(x / 7))))
      const n = [5, 6, 7][Math.floor(r() * 3)]
      const pillars = []
      for (let i = 0; i < n; i++) {
        const u = (i + 0.5) / n
        const edge = Math.abs(u - 0.5) * 2
        pillars.push({ x: Math.round(u * LW), w: 7 + Math.floor(r() * 3), h: Math.round(LH * (0.2 + 0.3 * edge + r() * 0.08)),
          cage: i === 1 || i === n - 2, ph: r() * 6.28 })
      }
      return { mode: 'main', ground, pillars }
    }
    const layouts = [
      [[0.12, 0.70, 0.20], [0.86, 0.60, 0.20], [0.50, 0.86, 0.28], [0.16, 0.30, 0.11], [0.84, 0.24, 0.12]],
      [[0.20, 0.82, 0.30], [0.80, 0.78, 0.16], [0.88, 0.40, 0.14], [0.10, 0.45, 0.12], [0.55, 0.22, 0.10]],
      [[0.14, 0.58, 0.16], [0.82, 0.84, 0.30], [0.46, 0.74, 0.14], [0.30, 0.26, 0.12], [0.88, 0.34, 0.10]]
    ]
    const defs = layouts[Math.floor(r() * layouts.length)]
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

  /** Obsidian column: stacked blocks with seams, purple specks and a lit left edge (reads as solid
   *  stone, not a light beam, even though the scene layer can only lighten the page). */
  obsidian(w, h, seed) {
    // Dark, nearly opaque obsidian (drawn on the normal-blend layer): block seams, purple specks, lit edges.
    const c = document.createElement('canvas')
    c.width = w
    c.height = h
    const g = c.getContext('2d')
    g.fillStyle = 'rgba(20,12,34,0.9)'
    g.fillRect(0, 0, w, h)
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const v = ((x * 73856093) ^ (y * 19349663) ^ (seed * 83492791)) >>> 0
        if (v % 7 === 0) {
          g.fillStyle = v % 3 ? 'rgba(70,44,110,0.95)' : 'rgba(120,80,180,0.95)'
          g.fillRect(x, y, 1, 1)
        }
      }
      if (y % 4 === 0) {
        g.fillStyle = 'rgba(8,4,16,0.95)'
        g.fillRect(0, y, w, 1)
        g.fillRect(((y / 4) % 2) * Math.floor(w / 2), y, 1, 4)
      }
    }
    g.fillStyle = 'rgba(110,86,160,0.95)'
    g.fillRect(0, 0, 1, h)
    g.fillRect(0, 0, w, 1)
    g.fillStyle = 'rgba(6,3,12,0.95)'
    g.fillRect(w - 1, 0, 1, h)
    return c
  }

  bob(isl) {
    return this.reduced?.matches ? 0 : Math.round(Math.sin(this.t * 0.35 + isl.ph))
  }

  /** Window-space water rectangles (lush-cave pools) for the axolotls. */
  pools() {
    if (!this.visible || !this.poolList || !this.poolList.length) return []
    return this.poolList.map(P => ({
      x0: this.rect.x + P.x0 * PX,
      x1: this.rect.x + (P.x0 + P.w) * PX,
      top: this.rect.y + (this.LH - P.hb) * PX,
      bottom: this.rect.y + (this.LH - P.hb + P.d) * PX,
      bank0: this.rect.x + Math.max(0, P.x0 - P.b) * PX,
      bank1: this.rect.x + Math.min(this.LW, P.x0 + P.w + P.b) * PX
    }))
  }

  /** Window-space points where shulkers can sit (outer End only). */
  perches() {
    if (!this.visible || !this.end || this.end.mode !== 'outer') return []
    const out = []
    for (const isl of this.end.islands) {
      const b = this.bob(isl)
      const k = this.end.islands.indexOf(isl)
      for (const dx of isl.perches) out.push({ x: this.rect.x + (isl.cx + dx) * PX, y: this.rect.y + (isl.top + b) * PX, isl: k })
    }
    return out
  }

  prop(g, name, x, y, alpha, flip = false) {
    if (!(this.sheet.complete && this.sheet.naturalWidth)) return
    const [bx, by, w, h] = PROP_BOX[name]
    g.globalAlpha = alpha
    if (flip) {
      g.save()
      g.translate(Math.round(x) + w, Math.round(y))
      g.scale(-1, 1)
      g.drawImage(this.sheet, bx, by, w, h, 0, 0, w, h)
      g.restore()
    } else {
      g.drawImage(this.sheet, bx, by, w, h, Math.round(x), Math.round(y), w, h)
    }
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
    } else if (type === 'bubble') {
      p.y = anywhere ? r() * LH : LH
      p.vy = -(4 + r() * 5)
      p.s = r() < 0.3 ? 2 : 1
    } else if (type === 'spore') {
      p.vy = 0.6 + r() * 1.2
      p.vx = (r() - 0.5) * 1.5
      if (!anywhere) p.y = -1
    } else if (type === 'sand') {
      p.y = LH * (0.55 + r() * 0.45)
      p.vx = -(10 + r() * 14)
      p.vy = (r() - 0.5)
      if (!anywhere) p.x = LW + 2
    } else if (type === 'sculk') {
      p.y = anywhere ? LH * (0.5 + r() * 0.5) : LH
      p.vy = -(1 + r() * 2)
      p.vx = (r() - 0.5) * 0.6
      p.life = anywhere ? r() : 1
    } else if (type === 'ash') {
      p.vy = 2 + r() * 3
      p.vx = -1 + (r() - 0.5) * 2
      if (!anywhere) p.y = -1
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
        if (!p.tex) p.tex = this.obsidian(p.w, p.h, p.x)
        const vis = Math.max(1, p.h - (E.ground[p.x] || 0) + 1)
        this.sctx.drawImage(p.tex, 0, 0, p.w, vis, x0, top, p.w, vis)
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
    const cfg = this.cfg || SCENES[this.world]
    const { lctx: g, LW, LH } = this
    g.clearRect(0, 0, LW, LH)
    this.sctx.clearRect(0, 0, LW, LH)
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
    if (cfg.rays) {
      for (let k = 0; k < 4; k++) {
        const x0 = ((k * 0.27 + this.t * 0.01) % 1) * (LW + LH * 0.5) - LH * 0.3
        const a = 0.05 + 0.03 * Math.sin(this.t * 0.6 + k * 1.7)
        g.fillStyle = `rgba(190,235,255,${a.toFixed(3)})`
        for (let y = 0; y < LH * 0.8; y++) g.fillRect(Math.round(x0 + y * 0.35), y, 3 + (k % 2), 1)
      }
    }
    if (this.end) this.drawEnd(g)
    if (this.ceil) {
      const C = this.ceil
      const off = Math.floor(this.t * C.speed) % C.L
      g.fillStyle = C.color
      for (let x = 0; x < LW; x++) g.fillRect(x, 0, 1, C.hts[(x + off) % C.L])
      for (const pr of C.props) {
        const [, , w] = PROP_BOX[pr.name]
        let x = (pr.x - off + C.L) % C.L
        if (x > C.L - w) x -= C.L
        if (x > LW || x < -w) continue
        this.prop(g, pr.name, x, C.hts[(pr.x + (w >> 1)) % C.L] - 1, 0.5)
      }
    }
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
        this.prop(g, pr.name, x, LH - hh - h + 1, layer === this.layers[this.layers.length - 1] ? 0.5 : 0.28, pr.flip)
      }
    })
    for (const P of this.poolList || []) {
      g.fillStyle = 'rgba(70,140,230,0.30)'
      g.fillRect(P.x0, LH - P.hb, P.w, P.d)
      const sh = 0.32 + 0.1 * Math.sin(this.t * 1.5 + P.x0)
      g.fillStyle = `rgba(170,220,255,${sh.toFixed(3)})`
      g.fillRect(P.x0, LH - P.hb, P.w, 1)
    }
    if (cfg.pulse && this.layers.length) {
      const fl = this.layers[this.layers.length - 1]
      const off = Math.floor(this.t * fl.speed) % fl.L
      const ci = Math.floor(this.t / 5)
      if (ci !== this.pulseI) {
        this.pulseI = ci
        this.pulseX = Math.round(this.rand() * LW)
      }
      const cyc = (this.t % 5) / 5
      const rr = Math.round(cyc * LW * 0.35)
      g.fillStyle = `rgba(70,230,245,${(0.45 * (1 - cyc)).toFixed(3)})`
      for (const x of [this.pulseX - rr - 1, this.pulseX - rr, this.pulseX + rr, this.pulseX + rr + 1]) {
        if (x < 0 || x >= LW) continue
        g.fillRect(x, LH - fl.hts[(x + off) % fl.L] - 1, 1, 2)
      }
    }
    const [cr, cg, cb] = cfg.pc
    this.parts.forEach((p, i) => {
      if (!still) {
        p.x += (p.vx + (cfg.p === 'petal' || cfg.p === 'bubble' || cfg.p === 'ash' ? Math.sin(this.t * 1.5 + p.ph) * 2 : 0)) * dt
        p.y += p.vy * dt
        if (cfg.p === 'ember') p.life -= dt * 0.25
        if (cfg.p === 'sculk') p.life -= dt * 0.15
        if (cfg.p === 'firefly') {
          p.vx = Math.max(-3, Math.min(3, p.vx + (this.rand() - 0.5) * dt * 4))
          p.vy = Math.max(-2, Math.min(2, p.vy + (this.rand() - 0.5) * dt * 4))
        }
        const out = p.y > LH + 2 || p.y < -2 || p.x < -4 || p.x > LW + 4 || p.life <= 0
        if (out) this.parts[i] = p.x < -4 && cfg.p !== 'firefly' ? Object.assign(this.particle(cfg.p, false), { x: LW + 2, y: this.rand() * LH }) : this.particle(cfg.p, false)
      }
      let a = 0.7
      if (cfg.p === 'firefly' || cfg.p === 'mote' || cfg.p === 'spore') a = 0.25 + 0.6 * Math.max(0, Math.sin(this.t * 2 + p.ph))
      if (cfg.p === 'ember') a = Math.max(0, p.life) * 0.95
      if (cfg.p === 'sculk') a = Math.max(0, p.life) * 0.7
      if (cfg.p === 'ash') a = 0.5
      g.fillStyle = `rgba(${cr},${cg},${cb},${a.toFixed(3)})`
      g.fillRect(Math.round(p.x), Math.round(p.y), p.s, p.s)
    })
    const { ctx } = this
    ctx.imageSmoothingEnabled = false
    ctx.clearRect(0, 0, this.rect.w, this.rect.h)
    ctx.drawImage(this.low, 0, 0, LW, LH, 0, 0, LW * PX, LH * PX)
    const sx = this.solid.getContext('2d')
    sx.imageSmoothingEnabled = false
    sx.clearRect(0, 0, this.rect.w, this.rect.h)
    if (this.end && this.end.mode === 'main') sx.drawImage(this.slow, 0, 0, LW, LH, 0, 0, LW * PX, LH * PX)
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
    this.solid.remove()
  }
}

// ---- world change: a pixel-block wipe, then the next world --------------------------------
const WIPE_COLOR = { overworld: '#1d2a18', cherry: '#3a1f2c', snow: '#1c2433', nether: '#2a0e0c', end: '#160f22',
  ocean: '#0e2a3a', lush: '#1a2e1a', desert: '#3a2e18', mushroom: '#2a1e2e', deepdark: '#071418' }

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
    for (const id of ['hmt-critters', 'hmt-scene', 'hmt-scene-solid', 'hmt-wipe', 'hmt-world-css']) document.getElementById(id)?.remove()
    const worldStyle = document.createElement('style')
    worldStyle.id = 'hmt-world-css'
    worldStyle.textContent = WORLD_CSS
    document.head.appendChild(worldStyle)
    const critters = new Critters()
    const scene = new Scene(undefined, () => critters.endMode)
    critters.perches = () => scene.perches()
    critters.pools = () => scene.pools()
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
