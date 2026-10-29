"""Render docs/preview.html — a static mock of the Hermes desktop using the real
customCSS from skins/minecraft.yaml — and record docs/preview.gif from it.

    python tools/make_preview.py           # writes docs/preview.html
    python tools/record_gif.py             # records docs/preview.gif (needs Chrome/Edge)
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def skin_css() -> str:
    text = (ROOT / "skins" / "minecraft.yaml").read_text(encoding="utf-8")
    m = re.search(r"^customCSS: \|-\n((?:  .*\n?)+)", text, re.M)
    return "\n".join(line[2:] for line in m.group(1).splitlines())


HTML = """<!doctype html>
<html class="dark"><head><meta charset="utf-8"><title>Hermes × Minecraft preview</title>
<style>
:root{--dt-background:#17191f;--dt-foreground:#e8e8e8}
html,body{margin:0;height:100%;background:#17191f;color:#e8e8e8;font-size:14px}
.app{display:grid;grid-template-columns:230px 1fr;grid-template-rows:1fr 30px;height:100vh}
[data-slot=sidebar]{background-color:#1b1d23;border-right:1px solid #3a3d44;padding:14px 10px;display:flex;flex-direction:column;gap:4px}
[data-slot=sidebar] h6{margin:6px 8px;color:#7bd34a;font-size:11px;letter-spacing:.12em}
[data-slot=row-button]{all:unset;display:block;padding:7px 10px;color:#cfcfcf;cursor:pointer}
main{display:flex;flex-direction:column;min-width:0}
[data-slot=aui_thread-viewport]{flex:1;overflow:auto;padding:24px 48px}
.composer-human-message{background:#2a3a22;padding:10px 14px;margin:0 0 18px auto;max-width:60%}
[data-slot=aui_user-message-root]{display:flex}
[data-slot=aui_assistant-message-content]{line-height:1.6;max-width:760px}
[data-slot=tool-block]{padding:8px 12px;margin:10px 0;font-family:monospace;color:#55ffff}
[data-slot=aui_response-loading]{display:flex;align-items:center;color:#a0a0a0;margin-top:8px}
[data-slot=composer-surface]{margin:0 48px 22px;padding:14px;color:#888}
[data-slot=statusbar]{grid-column:1/3;display:flex;align-items:center;gap:18px;padding:0 14px;font-size:12px}
[data-slot=button]{all:unset;padding:6px 14px;cursor:pointer}
[data-slot=aui_intro]{text-align:center;padding:30px 0 10px;color:#a0a0a0}
.wordmark{font-size:30px;color:#fff;margin:0 0 4px}
</style>
<style id="hermes-desktop-custom-css">__CSS__</style></head>
<body><div class="app">
<aside data-slot="sidebar">
  <h6>SESSIONS</h6>
  <button data-slot="row-button" data-active="true">⛏ Minecraft theme</button>
  <button data-slot="row-button">🧱 Build a redstone clock</button>
  <button data-slot="row-button">📖 Enchanting guide</button>
  <div style="flex:1"></div>
  <button data-slot="button" data-variant="default">+ New world</button>
</aside>
<main>
  <div data-slot="aui_thread-viewport">
    <div data-slot="aui_intro"><div class="wordmark">Hermes</div><p>What should we build today?</p></div>
    <div data-slot="aui_user-message-root"><div class="composer-human-message">幫我做一個 Minecraft 主題</div></div>
    <div data-slot="aui_assistant-message-content">
      <h2>Crafting your theme</h2>
      <p>Placing <strong>grass blocks</strong>, polishing <code>stone</code> buttons and adding an <a href="#">enchanted glint</a>.</p>
      <div data-slot="tool-block">┃ ⛏ terminal  python tools/build_skin.py</div>
      <div data-slot="aui_response-loading" data-message-streaming="true">mining…</div>
    </div>
  </div>
  <div data-slot="composer-surface"><div data-slot="composer-rich-input">Send a message…</div></div>
</main>
<footer data-slot="statusbar"><span>● minecraft</span><span>claude-opus</span><span style="margin-left:auto">♥♥♥♥♥♥♥♥♥♡</span></footer>
</div>
<script>
/* preview.html#t=<ms> freezes every CSS animation at that time (used by record_gif.py) */
(function(){var m=location.hash.match(/t=(\\d+)/);if(!m)return;var t=+m[1];
function seek(){document.getAnimations().forEach(function(a){a.pause();a.currentTime=(a.animationName==='mc-sky'?20000+t:t);});}
document.fonts.ready.then(function(){seek();requestAnimationFrame(seek);});})();
</script></body></html>
"""


def main() -> None:
    out = ROOT / "docs" / "preview.html"
    out.write_text(HTML.replace("__CSS__", skin_css()), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
