# 小鱼爱可可 · 可可爱拼豆 + 可可听故事

这是整合后的**一个网站工程**，包含原有「可可爱拼豆」与新做的「可可听故事」。

- **首页** `docs/index.html`：两张入口卡片。
- **可可爱拼豆** `docs/beads/index.html`：来自用户提供的完整 HTML，**逐字节原样保留，不动拼豆算法**。
- **可可听故事** `docs/stories/`：**随便听听**（真人预录音、随机播放）/ **我想听这个**（输入中文，GPT-SoVITS 用小鱼的声音朗读）。
- **小鱼管理员页面** `docs/admin/`：用管理员密钥登录，上传新故事、浏览器麦克风录音、修改标题和简介、删除故事、录入自己的声音样本。
- **故事库** `docs/story-archive/catalog.json` + `docs/story-archive/audio/`：公开音频和目录，适合上传 GitHub Pages。管理页提交变更后需要**同步 GitHub**才会更新线上静态故事库。
- **Windows 本地后端** `server/gateway.py`：Python 标准库，故事管理 API + GPT-SoVITS `/tts` 转发。使用两种独立密钥。它不包含 GPT-SoVITS 代码和模型权重。

## 先看运行与上线关系

```
访客打开 https://yakidle.github.io/
     ├─ 可可爱拼豆 → 纯浏览器运行，不用你的电脑开机
     └─ 可可听故事
           ├─ 随便听听 → GitHub Pages 上的真人音频，电脑关机仍能播放
           └─ 我想听这个 → HTTPS Tunnel → 你的 Windows 后端
                                             → GPT-SoVITS → RTX 4070 Laptop
```

**特别说明：GitHub Pages 不能运行 Python 或 GPU 推理服务。** 你的电脑要保持开机、运行模型、运行后端、运行 Tunnel。「我想听这个」才能生成声音。预录故事可以独立在线播放，但必须先发布到 GitHub。

## 1. 先在 Windows 安装 GPT-SoVITS

从官方 [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) 下载安装**Windows 整合包**，确保解压目录里有：

```
D:\GPT-SoVITS\
  api_v2.py
  runtime\python.exe
  GPT_SoVITS\configs\tts_infer.yaml
```

注意官方模型权重体积较大，必须另外准备齐全。4070 Laptop 8GB 显存建议先用官方允许的较省显存模型版本。建议先按官方说明运行并确认推理正常。本项目只能调用模型，不保证某个整合包的 CUDA/依赖必然适配。

## 2. 本地一键启动

**非常重要：如果要长期维护 GitHub 网站，请把本项目直接放在 GitHub Desktop 管理的 `yakidle.github.io` 仓库工作目录里，并从该目录运行启动脚本。** 这样管理员上传/删除的音频才会由 GitHub Desktop 自动识别为待同步变更。不要一边运行下载文件夹中的副本，一边用 GitHub Desktop 管理另一个拷贝，否则故事不会自动出现在待推送的仓库里。

1. 将 GPT-SoVITS 整合包和本项目分别放在电脑上，**网站工程推荐放到 GitHub Desktop 管理的原网站仓库目录**。
2. 双击本项目 `START_WINDOWS.bat`。
3. 首次按提示输入 GPT-SoVITS 的目录，例如 `D:\GPT-SoVITS`。
4. 启动脚本生成本机 `settings.local.json`，包含随机的两串不同密钥：
    - `admin_key`：**你本人独有的管理员密钥**。用在 `/admin/`，可以改故事、上传声音，绝对不能分享。
    - `listener_key`：**可以单独告诉可可的听故事暗号**。只允许调用 TTS，不允许编辑故事或更换声音。
5. 模型与网站后端会分别启动窗口。网页本地地址：http://127.0.0.1:7865/ ；管理员：http://127.0.0.1:7865/admin/ 。
6. 进入管理员页面，输入 `admin_key`，点击「连接管理后台」；再上传 5–10 秒自己的普通话参考音频、填写这段录音对应的原文，点「保存我的声音」。
7. 在故事页「我想听这个」中输入 `listener_key`，写中文文字，试着生成 WAV。长文本（最多1200字）由网关分段调用 GPT-SoVITS，再拼接 WAV。

声音样本与管理密钥保存在本机 `data/` 和 `settings.local.json`，**不要放进 GitHub**。

## 3. 随便听听：持续添加、修改、删除故事

打开 `http://127.0.0.1:7865/admin/` 登录管理员。

- **上传新录音**：填写故事标题，可填简介，选择 MP3/WAV/M4A/OGG/WebM/FLAC 音频，点击「保存到故事盒子」。建议 MP3，以兼容更多手机浏览器。每篇最大 24MB。故事文件保存在 `docs/story-archive/audio/`。
- **直接录音**：点击「开始麦克风录音」；浏览器申请麦克风授权后开始录制；讲完点「结束录音」，试听、保存。浏览器录音格式由浏览器决定，WebM 可能无法在部分 iPhone 浏览器播放，长期保存建议自己转成 MP3 后上传。
- **修改信息**：在故事列表点「改信息」，修改标题和简介。
- **删除旧故事**：点「删除」，确认后删除本机音频并从 `catalog.json` 里移除。此操作不可撤销，建议重要录音自行备份。

**重要：管理员增删改只会先改变你本地项目的 `docs/story-archive/`。** 如果你希望已经上线的 `https://yakidle.github.io/` 同步故事，需要通过 **GitHub Desktop** 对该项目进行 `Commit` 和 `Push origin`（或用 Git 命令推送）。GitHub Pages 不是数据库，不能靠浏览器上传就自动改写远端仓库。本项目**不在前端保存 GitHub 令牌**。

如果你打开的是通过 Cloudflare Tunnel 访问的本地网页，故事库会立即看到刚保存的录音；如果打开的是 GitHub Pages，需等推送发布后才能看到新故事。相反，在 GitHub Pages 上已经发布的故事，你电脑即使关机也可以播。

## 4. 把新网站替换原 yakidle.github.io 的首页

你的旧站是 `https://yakidle.github.io/`。**建议先保存原仓库副本或创建分支**，再更新；千万不要直接删除原仓库里的唯一一份代码。

1. 在 GitHub Desktop 打开承载 `yakidle.github.io` 的仓库（已确认公开仓库为 [yakidle/yakidle.github.io](https://github.com/yakidle/yakidle.github.io)）。
2. 把这个工程的**所有源文件**（`docs/`、`server/`、`scripts/`、`START_WINDOWS.bat` 等）复制到仓库根目录。
3. 不要上传本机 `settings.local.json`、`data/`，`.gitignore` 已经排除它们。
4. 从这个**仓库工作目录**运行 `START_WINDOWS.bat`，之后所有管理更新都会直接写入仓库的 `docs/story-archive/`。在仓库 `Settings → Pages → Build and deployment` 选择 `Deploy from a branch`，branch=`main`，folder=`/docs`；保存。如果仓库的发布方式原本是 `/ (root)`，请务必改为 `/docs`。
5. `Commit`、`Push origin`，等待 Pages 发布。新的 `https://yakidle.github.io/` 变为「小鱼爱可可」首页，旧拼豆转到 `https://yakidle.github.io/beads/`，新故事位于 `https://yakidle.github.io/stories/`。
6. **只替换发布目录，不要移除以前保存的其他资料或 Git 历史。** 需要在原仓库更新已有文件而非新建另一个无关仓库。

### 如果发布后首页变成 404

检查 GitHub Pages 是否真的选择了 `main /docs`，且仓库中的 `docs/index.html` 存在。对于 `yakidle.github.io` 这样的用户主页仓库，GitHub Pages 使用的根路径就是 `/`。如果你选择建立普通子目录仓库，访问路径会带仓库名，导航也要相应调整。

## 5. 让可可从 GitHub 页面调用你本地 RTX 4070

**推荐固定域名的 Cloudflare Named Tunnel**（需要一个可管理 DNS 的域名配置在 Cloudflare 上），将公网 `https://...` 指向你电脑的 `http://127.0.0.1:7865`。Cloudflare 临时 Quick Tunnel 也能测试，但它的 HTTPS 地址每次启动可能不同。

1. Windows 安装 [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)。
2. 保持 `START_WINDOWS.bat` 打开的模型与网站窗口在线。
3. 测试时可双击 `START_TUNNEL.bat`，它会运行 Quick Tunnel 并显示 `https://xxxx.trycloudflare.com`。**这是演示用临时地址，不是固定域名。**
4. 用文本编辑器打开 `docs/site-config.js`，将其中的 `apiBase: ''` 填入**真实的**公网 HTTPS URL，例如：`apiBase: 'https://xxxx.trycloudflare.com'`。这个地址是公开信息，不要填写密钥。
5. `Commit`、`Push origin`，等待 GitHub Pages 更新。可可打开 GitHub 网站后，在「我想听这个」填写你单独给她的 `listener_key` 即可使用。
6. 如果 Quick Tunnel 重新启动、URL 变了，则重新编辑 `docs/site-config.js` 并推送。只有 Named Tunnel 才适合长期固定地址。网站上也有「声音服务连不上？」可临时改当前浏览器的服务器地址。

本地 API 只监听 `127.0.0.1:7865`，GPT-SoVITS 模型 API 只监听 `127.0.0.1:9880`。**不要直接把 9880 端口映射到公网。** 只映射受认证与限流保护的网关即可。

## 6. 文件结构

```
Xiaoyu-Loves-Keke/
├─ docs/                      # GitHub Pages 发布目录
│  ├─ index.html              # 网站首页
│  ├─ common.css              # 新页面统一风格
│  ├─ site-config.js          # 只存公开的网关 URL，绝不存密钥
│  ├─ beads/index.html        # 原始拼豆 HTML，未修改
│  ├─ stories/index.html      # 听故事页面
│  ├─ stories/stories.js      # 真人录音 + AI TTS
│  ├─ admin/index.html        # 管理员界面
│  ├─ admin/admin.js          # 上传/录音/编辑/删除
│  └─ story-archive/
│     ├─ catalog.json         # 真人故事清单
│     └─ audio/               # 真人故事音频（需要你后续添加）
├─ server/gateway.py          # 纯 Python API 后端
├─ scripts/                   # 启动脚本
├─ tests/                     # 基础 API 联调测试
├─ START_WINDOWS.bat
├─ START_TUNNEL.bat
├─ settings.local.example.json
├─ .gitignore
└─ README.md
```

## 7. 安全、限制与隐私

- 仅用于自己或已授权的声音，不要未经同意模仿别人。
- `admin_key` 和 `listener_key` 绝不写入 `docs/` 或公开仓库，管理员密钥严禁交给访客。
- 模型调用需要 `listener_key`，限制为全站每分钟最多 5 次/每小时最多 30 次，且同一时间只执行一个推理。不是企业级 DDoS 防护，如面向多人公开还需进一步加身份认证、配额、日志审计。
- 真人故事录音放在 `docs/story-archive/audio/`，一旦推送 GitHub 就是**公开文件**。不适合放含隐私的录音；删除后 Git 历史或第三方缓存可能仍留有副本。敏感音频应使用私有对象存储并增加访问控制。
- 浏览器存储的只是当前浏览器设置的推理服务 URL；访问暗号只在该页面输入时用于请求，未写入 GitHub 代码。
- 提供的项目包**不含用户录音、模型权重或 GPT-SoVITS 主程序**，必须先另行安装并添加录音。
- 一次大故事生成可能需要较长时间；如果显存不足，优先检查模型设置、参考音频以及 CUDA 驱动。
- 旧拼豆 HTML 的原有第三方色卡数据和使用条款不因整合而改变。

## 8. 项目测试

不依赖 GPU 的联调测试：在项目根目录执行 `python -m unittest discover -s tests -v`。它使用模拟 GPT-SoVITS 返回的 WAV，检查管理员权限、故事增删、参考音频保存、中文文字合成与网页路径。真实模型的 CUDA 运行仍需你在 Windows 上实际验证。
