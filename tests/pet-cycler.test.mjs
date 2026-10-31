
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, dirname } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
// Load the built plugin with tiny stand-ins for the Hermes SDK / React imports.
const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const dir = mkdtempSync(join(tmpdir(), 'hmt-pc-'))
const src = readFileSync(join(root, 'desktop-plugins/minecraft-activity/plugin.js'), 'utf8')
writeFileSync(join(dir, 'plugin.mjs'), src.replace("from '@hermes/plugin-sdk'", "from './sdk.mjs'").replace("from 'react/jsx-runtime'", "from './jsx.mjs'"))
writeFileSync(join(dir, 'sdk.mjs'), "export const atom=v=>({get:()=>v,set:n=>{v=n}});export const host={};export const PALETTE_AREA='p';export const STATUSBAR_AREAS={};export const useValue=a=>a.get()")
writeFileSync(join(dir, 'jsx.mjs'), 'export const jsx=()=>null;export const jsxs=jsx')
const { PetCycler, WORLD_PETS, PETS } = await import(pathToFileURL(join(dir, 'plugin.mjs')).href)
let fails = 0
const ok = (c, m) => { console.log(c ? 'ok  ' : 'FAIL', m); if (!c) fails++ }
const sleep = ms => new Promise(r => setTimeout(r, ms))
function mk({ slug = 'enderman', enabled = true, installed = PETS, delay = 0, galleryFail = 0 } = {}) {
  const st = { slug, enabled, installed: new Set(installed), galleryFail }, selects = [], store = {}
  let t = 0
  const req = async (m, p) => { if (delay) await sleep(delay)
    if (m === 'pet.info.meta') return { enabled: st.enabled, slug: st.slug }
    if (m === 'pet.gallery') { if (st.galleryFail-- > 0) throw new Error('offline'); return { pets: PETS.map(s => ({ slug: s, installed: st.installed.has(s) })) } }
    if (m === 'pet.select') { selects.push(p.slug); st.slug = p.slug; return { ok: true } } }
  const pc = new PetCycler({ get: (k, d) => k in store ? store[k] : d, set: (k, v) => { store[k] = v } }, req, () => t)
  pc.rand = (() => { let s = 7; return () => (s = (s * 9301 + 49297) % 233280) / 233280 })()
  return { pc, st, selects, store, adv: ms => { t += ms } }
}
let a = mk()
ok(a.pc.mode === 'manual', 'default mode is manual')
await a.pc.onWorld('nether'); ok(a.selects.length === 0, 'manual: world change does nothing')
await a.pc.setMode('world', 'end'); ok(a.st.slug === 'shulker' && a.store.petMode === 'world', 'world: End while showing enderman -> shulker')
const n0 = a.selects.length; await a.pc.onWorld('end'); ok(a.selects.length === n0, 'same world again: no switch')
await a.pc.onWorld('nether'); ok(WORLD_PETS.nether.includes(a.st.slug), `world: Nether -> ${a.st.slug}`)
await a.pc.onWorld('deepdark'); ok(a.st.slug === 'warden', 'world: Deep Dark -> warden')
await a.pc.onWorld('ocean'); ok(a.st.slug === 'squid', 'world: ocean -> squid')
let b = mk({ installed: PETS.filter(p => p !== 'shulker') }); await b.pc.setMode('world', 'end')
ok(!b.selects.includes('shulker') && b.st.slug === 'enderman', 'pet not installed is never passed to pet.select')
let c = mk({ enabled: false }); await c.pc.setMode('world', 'nether'); await c.pc.setMode('random')
ok(c.selects.length === 0, 'pet turned off: no switching at all')
let d = mk({ slug: 'pig', delay: 5 }); await d.pc.setMode('world', 'cherry'); d.selects.length = 0
const p1 = d.pc.onWorld('nether'); const p2 = d.pc.onWorld('end'); await p1; await p2; await sleep(80)
ok(d.selects.every(s => WORLD_PETS.end.includes(s)) && WORLD_PETS.end.includes(d.st.slug), `fast world changes: only the latest world applies (${d.selects})`)
let q = mk({ slug: 'pig', delay: 5 }); await q.pc.setMode('world', 'cherry')
const q1 = q.pc.onWorld('nether'); const q2 = q.pc.onWorld('end'); await q1; await q2; await sleep(80)
const qn = q.selects.length; q.adv(2 * 60 * 1000); q.pc.tick(); await sleep(80)
ok(q.pc.applied === 'end' && q.selects.length === qn, 'queued world switch is recorded: no extra draw a minute later')
let e = mk({ delay: 5 }); await e.pc.setMode('world', 'cherry'); e.selects.length = 0
const p3 = e.pc.onWorld('nether'); e.pc.setMode('manual'); await p3; await sleep(40)
ok(e.selects.length === 0, 'world -> manual mid-request: nothing selected')
let f = mk({ delay: 5 }); const p4 = f.pc.setMode('random'); f.pc.destroy(); await p4; await sleep(40)
ok(f.selects.length === 0, 'destroyed mid-request: nothing selected')
let g = mk({ slug: 'pig' }); await g.pc.setMode('random'); let rep = 0
for (let i = 0; i < 40; i++) { const before = g.st.slug; g.adv(10 * 60 * 1000 + 1); g.pc.tick(); await sleep(0); await sleep(0); if (g.st.slug === before) rep++ }
ok(rep === 0, 'random: never the same pet twice in a row (40 switches)')
let h = mk({ slug: 'pig' }); await h.pc.setMode('random'); const nh = h.selects.length; h.adv(4 * 60 * 1000); h.pc.tick(); await sleep(0)
ok(h.selects.length === nh, 'random: nothing before the 5-minute minimum')
let k = mk({ galleryFail: 1 }); await k.pc.setMode('world', 'nether')
ok(k.selects.length === 0, 'offline on entering a world: no switch yet')
k.adv(30 * 1000); k.pc.tick(); await sleep(5); ok(k.selects.length === 0, '...no retry before a minute')
k.adv(31 * 1000); k.pc.tick(); await sleep(5); await sleep(5); ok(WORLD_PETS.nether.includes(k.st.slug), '...retried after a minute and applied')
let m = mk({ slug: 'mooshroom' }); await m.pc.setMode('world', 'mushroom'); ok(m.selects.length === 0 && m.st.slug === 'mooshroom', 'one-pet world already showing it: unchanged')
ok(Object.keys(WORLD_PETS).length === 10 && Object.values(WORLD_PETS).flat().every(p => PETS.includes(p)), '10 worlds, every pool pet is a real pet')
rmSync(dir, { recursive: true, force: true })
process.exitCode = fails ? 1 : 0
