# Industrial Frontier · 工业数字化前沿

独立的静态资讯网站。无需服务器、无需数据库。GitHub Pages 负责公开网页，GitHub Actions 负责每日抓取 RSS 与更新 JSON。

## 首次部署

1. 新建公开 GitHub repository（例如 `industrial-frontier`）。上传本文件夹中的 **全部内容**，必须保留 `.github/workflows/update.yml` 的路径（以 GitHub 网页的 **Add file → Upload files** 上传时，可将文件夹展开，拖入全部文件与子目录；如果浏览器无法上传隐藏目录，在仓库内手动 Create new file，路径填 `.github/workflows/update.yml`，粘贴内容）。
2. Repository → Settings → Pages → Build and deployment → Deploy from a branch → `main` / `(root)` → Save。
3. Repository → Settings → Actions → General → Workflow permissions → 选择 **Read and write permissions** → Save。
4. Actions → Refresh industrial intelligence → Run workflow。默认每天 **新加坡时间 08:15 左右**触发（GitHub 定时任务可能延迟）。更新成功后 Actions 自动提交 `data/news.json`，无需每天手工 Commit。
5. 网页地址通常为 `https://<你的GitHub用户名>.github.io/industrial-frontier/`，如果仓库名称不同，以 Pages 页面展示的 URL 为准。

## 可选：AI 中文摘要

不设置密钥也能运行，但自动新增内容将主要保留源语言（通常英文），并附中文的方向性创业启发。若需要新增内容**自动生成中文标题、摘要和创业启发**：

Settings → Secrets and variables → Actions → New repository secret → Name: `OPENAI_API_KEY` → Value: 你的 API Key。

代码只会把公开 RSS 中的新闻标题、简述和类别发送到 API。**不会上传公司内部文件**。API 会产生独立计费，请设置额度限制。默认使用 `gpt-4.1-mini`，可改 `update.yml` 中 `OPENAI_MODEL` 为当前可用模型。模型请求失败会自动保留英文原文，不中断新闻更新。

## 图片策略（V3）

- 优先使用 RSS 资讯源提供的 `https://` 图片（如果图片失效，网页自动回退）。
- 缺少新闻图片时，按六种主题分配 **六张不同的本地备用图**：`assets/ai.svg`、`assets/monitor.svg`、`assets/data.svg`、`assets/robot.svg`、`assets/energy.svg`、`assets/startup.svg`。
- 所有备用图为本站自制 SVG 插画，非新闻现场实拍；本地预览不会依赖外部图片服务器。
- **打开 index.html** 可以直接查看内置的初始新闻；部署到 Pages 后网页优先读取 `data/news.json`，因此每日更新会立即生效。

## 修改方向

- `scripts/update_news.py` 的 `QUERIES`：新增或调整搜集方向。
- `index.html` 的 `groups`：修改筛选项（应与 Python 的类别保持一致）。
- `data/news.json`：可人工维护精选首屏资讯，但下一次自动抓取会替换新闻；适合测试 UI。

## 注意

Google News RSS 是资讯发现渠道，其新闻标题、链接和时间受聚合服务影响。网站展示外部新闻的简述和原文链接，不转载全文。AI 仅根据标题和 RSS 简述总结，可能遗漏上下文；创业启发仅供假设探索，不视为已验证市场。
