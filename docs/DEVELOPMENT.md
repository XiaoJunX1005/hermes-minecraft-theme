# 開發說明

[← 回到 README](../README.md)（[English](../README.en.md)）　·　[詳細說明](DETAILS.md)

素材全部由 `tools/` 裡的 Python 程式產生，需要 Python 3.10 以上與 Pillow。請修改 `src/` 或 `tools/`，不要直接改 `skins/*.yaml`（那是產生出來的檔案）。

```bash
pip install pillow
python tools/make_pets.py         # 7 隻寵物 → pets/*/、docs/pets.gif、docs/pets/*.gif（會檢查每格不貼邊）
python tools/make_activity.py     # 活動圖示 → desktop-plugins/minecraft-activity/plugin.js、docs/activity.gif
python tools/build_skin.py        # 10 個世界 → skins/*.yaml、docs/islands.gif、docs/thinking.gif
python tools/build_skin.py --install                 # 產生並安裝到本機，保留目前的選擇
python tools/build_skin.py --install --skin=minecraft-end --pet=bee
python tools/make_preview.py && python tools/record_gif.py   # 預覽頁與 docs/preview.gif（需要 Chrome 或 Edge）
```

| 檔案 | 用途 |
|---|---|
| `src/skin.base.yaml` | 配色、終端機提示文字、品牌文字 |
| `src/desktop.css` | 桌面版樣式與動畫（`{{...}}` 由 build 依世界填入） |
| `tools/voxel.py` | 5 種空島與渲染器 |
| `tools/make_icons.py` | 主題內建的思考中圖示（無插件時使用） |
| `src/activity-plugin.js` | 活動圖示插件原始碼（`make_activity.py` 會把圖嵌入並輸出到 `desktop-plugins/`） |
| `tools/pixels.py` | 草地、泥土等材質 |
| `tools/blocks.py` | 各世界側欄的方塊材質（16×16，壓暗讓文字好讀） |
| `tools/pet3d.py` | 寵物用的立體方塊渲染器（96×104 像素，可半透明、自發光） |
| `tools/make_pets.py` | 7 隻寵物的模型、動作與特效 |
| `tools/critters_art.py` | 飛行生物與界伏蚌的像素圖 |
| `tools/scene_art.py` | 背景地標（各種樹、巨型蕈、冰屋、終界城、水晶、傳送門） |

Hermes 對主題內嵌 CSS 有 32 KiB 上限，目前每個世界約 30 KiB；超過時 `build_skin.py` 會直接報錯。另一版極簡風格「Voxel Lantern」保留在 git tag `voxel-lantern`。

