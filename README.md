<div align="center">

# ⛏ Hermes × Minecraft

非官方的 Minecraft 風格 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 主題：十個會動的世界、在視窗裡遊蕩的生物、跟著工作內容變化的圖示。

![worlds](docs/worlds.gif)

<sub>示意圖：插件實際畫出的背景與生物，疊在模擬頁面上錄製，不是 Hermes 實機截圖。</sub>

</div>

## 安裝與更新

**Windows（PowerShell）**

```powershell
irm https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.ps1 | iex
```

**macOS / Linux / WSL / Git Bash**

```bash
curl -fsSL https://raw.githubusercontent.com/XiaoJunX1005/hermes-minecraft-theme/main/install.sh | bash
```

再執行一次就是更新，會保留你目前選的世界和寵物。用另一台電腦連線使用時，那台電腦也要執行一次。

## 切換世界和寵物

```bash
hermes config set display.skin minecraft-nether   # 世界，例如 minecraft、minecraft-end；完整列表見詳細說明
hermes pets select creeper-blocky                 # 寵物；hermes pets off 關閉
```

桌面版也可以在「外觀」設定裡選。世界預設每 4–8 分鐘自動換一次，按 Ctrl+K（⌘K）搜尋「Minecraft」可以關閉或立刻換。

還原：`hermes config set display.skin default`

## 更多

- [詳細說明](docs/DETAILS.md)：每個世界的場景與生物、寵物列表、活動圖示、怎麼惹毛蜜蜂、用另一台電腦連線。
- [開發說明](docs/DEVELOPMENT.md)：想自己修改主題或重新產生素材時再看。

## 授權

- 程式碼與自行繪製的圖像：MIT，見 [LICENSE](LICENSE)。
- 字型 [Zpix](https://github.com/SolidZORO/zpix-pixel-font)：**個人與教育用途免費，商業用途需向作者購買授權**。本專案只透過 CDN 載入，不附帶字型檔。
- 非官方粉絲作品，與 Mojang Studios、Microsoft 無關。Minecraft 是 Mojang Synergies AB 的商標。
