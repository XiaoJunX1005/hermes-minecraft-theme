<div align="center">

# ⛏ Hermes × Minecraft Theme

**Minecraft 風格、會動的 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 主題（桌面版 / TUI / CLI）**

![preview](docs/preview.gif)

<sub>預覽圖是用真實主題 CSS 套在模擬頁面上錄的示意圖。</sub>

</div>

## ✨ 特色

| | 動畫 / 效果 |
|---|---|
| 🏝 **漂浮空島** | 新工作階段畫面中央有一座慢慢旋轉、漂浮的體素空島；5 個世界可選 |
| 🔤 **Zpix 像素字** | 中英數字全 12px 點陣（繁中可用），jsDelivr 線上載入，離線退回微軟正黑體 |
| 🌌 **夜空** | 上方星星與緩慢飄動的方塊雲（顏色隨世界變化） |
| 🟩 **經驗值條** | Hermes 回覆時輸入框下方跑 XP 條 |
| ⛏ **挖礦中…** | 「思考中」換成迷你旋轉草方塊（32×32 高細節材質） |
| 💜 **附魔光澤** | 你的訊息泡泡有紫色附魔光掃過 |
| 🌱 **地表狀態列** | 每個世界自己的地表條（草地 / 緋紅菌岩 / 終界石 / 雪地 / 落花草地） |
| 🪨 **石頭按鈕** | 石材紋理 + 立體斜角，滑過變藍底黃字 |
| 🐸 **苦力怕寵物** | 4 種造型可挑，9 種動畫狀態 |

## 🏝 世界

![islands](docs/islands.gif)

| 主題 | 世界 | 空島 | 主色 / 標語 |
|---|---|---|---|
| `minecraft` | 主世界 | 草地、樹、小池塘、燈 | 草綠 · *Also try Minecraft!* |
| `minecraft-nether` | 地獄 | 緋紅菌岩、熔岩池、緋紅/詭異蕈、玄武岩 | 熔岩橘 · *Also try the Overworld!* |
| `minecraft-end` | 終界 | 終界石、黑曜石柱 + 終界水晶、歌萊植物、小浮石 | 紫 · *The End?* |
| `minecraft-snow` | 雪原 | 雪地、雲杉、冰塊、冷光燈 | 冰藍 · *Brrr! Bring a coat!* |
| `minecraft-cherry` | 櫻花林 | 櫻花樹、落花、池塘 | 櫻粉 · *Petals everywhere!* |

切換：`hermes config set display.skin minecraft-nether`（或在 Appearance 直接選），一秒內即時換。

## 🐸 苦力怕

![creepers](docs/creepers.gif)

| 寵物 | 造型 |
|---|---|
| `creeper-blocky`（預設） | 方正 Q 版：方頭方身、方眼、經典嘴，有光影 |
| `creeper-carved` | 稜角立體：直角寬頭、亮頂面、凹刻的臉 |
| `creeper-tall` | 接近原版比例：頭較小、身體較長 |
| `creeper-buddy` | 圓潤 Q 版：圓眼、亮點、腮紅 |
| `lantern-buddy` | 另一隻原創小燈籠 |

切換：`hermes pets select creeper-carved`

## 📦 安裝

```powershell
irm https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.ps1 | iex
```

```bash
curl -fsSL https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.sh | bash
```

手動：把 `skins/*.yaml` 複製到 Hermes home 的 `skins/`（Windows：`%LOCALAPPDATA%\hermes\skins\`），`pets/*` 複製到 `pets/`。

**還原：** `hermes config set display.skin default`，寵物 `hermes pets off`。

## 🛠 開發

```
src/skin.base.yaml      調色盤、spinner、品牌文字、tool emoji
src/desktop.css         桌面版 customCSS（{{...}} 由 build 依世界填入）
tools/voxel.py          5 種空島 + 光線投射渲染器
tools/pixels.py         材質（32×32 草地 / 泥土）
tools/build_skin.py     → skins/*.yaml（5 個世界）+ docs/islands.gif、grass-block.gif
tools/make_creeper.py   → pets/creeper-*/ + docs/creepers.gif
tools/make_lantern.py   → pets/lantern-buddy/
tools/make_preview.py   → docs/preview.html；tools/record_gif.py → docs/preview.gif
```

```bash
pip install pillow
python tools/make_creeper.py
python tools/build_skin.py --install                     # 主世界 + creeper-blocky
python tools/build_skin.py --install --skin=minecraft-end
```

每個世界的 customCSS 約 27 KiB（上限 32 KiB，超過會直接報錯）。極簡「Voxel Lantern」版保留在 git tag `voxel-lantern`。

## 📄 License

程式碼 MIT。Zpix 字型屬原作者與其授權（CDN 連結載入，未隨附）。非官方粉絲作品，與 Mojang / Microsoft 無關；*Minecraft* 是 Mojang Synergies AB 的商標。
