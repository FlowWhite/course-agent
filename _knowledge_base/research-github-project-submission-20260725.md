# Course Agent GitHub 提交调研笔记

调研日期：2026-07-25
调研目标：为 Course Agent 制定安全、可复现的 GitHub 提交流程，不提交密钥、运行数据或上传的课程资料。

## 关键问题

1. GitHub 官方推荐的初始化、提交和推送流程是什么？
2. 哪些 Course Agent 本地文件必须排除，尤其是 `.env`、Docker 数据卷、日志和上传资料？
3. 如何在 GitHub 上安全保存部署所需的环境变量说明？

## 发现

### GitHub 官方提交流程（第 1 轮）

- 对于已有本地项目，GitHub 官方建议先在网页端创建一个**空仓库**；导入现有项目时不要预先勾选 README、`.gitignore` 或许可证，以免制造首次推送的合并冲突。
- 官方明确要求：绝不能把密码、API Key 等敏感信息 `git add`、提交或推送到远程仓库。Course Agent 的 DeepSeek 密钥必须保留在本地 `.env`，仅提交变量名示例文件。
- `.gitignore` 应提交到仓库根目录，使所有协作者共享忽略规则；已经被 Git 跟踪的敏感文件需要先取消跟踪，单纯新增忽略规则不会把它从历史记录中移除。
- 现有项目可通过 Git 命令、GitHub CLI 或 GitHub Desktop 发布。当前项目适合先做提交前审计，再使用 Git 命令连接新建的空仓库。

### GitHub Secret Protection（第 2 轮）

- GitHub Push Protection 的目标是在推送前阻止硬编码凭据进入仓库；用户账号在向公开仓库推送时默认受到该保护。
- 这只能作为第二道防线，不能代替项目内的 `.gitignore` 和提交前审计，因为密钥一旦进入 Git 历史仍需要轮换与清理。
- 若未来将仓库设为公开，建议在仓库 Settings 的 Security 配置中启用可用的 Secret Scanning / Push Protection，并在首次公开前轮换当前 DeepSeek API Key。

### GitHub Actions 最小 CI（第 3 轮）

- GitHub 官方建议在 Python 工作流中使用 `actions/setup-python@v5` 固定运行时版本，并通过 `pip install -r requirements.txt` 安装依赖后执行本地同一套测试命令。
- 前端工作流使用 `actions/setup-node@v4` 和已经提交的 `package-lock.json` 执行 `npm ci`，再运行 `npm run build`。
- Course Agent 的首版 CI 不使用真实 DeepSeek Key、课程资料或生产 PostgreSQL；只验证不依赖外部服务的单元测试、Python 语法和 Vue 构建。

## 阶段摘要 (第1轮)

Course Agent 上 GitHub 的关键不是“直接推送”，而是先构造安全提交边界：源代码、数据库初始化脚本、无密钥配置示例和文档可以提交；`.env`、运行数据、日志、上传课程资料和本地会话库必须排除。

### 阶段摘要 (第2轮)

公开展示应采用“代码 + 空白配置示例 + 演示数据说明”的仓库形式。真实课程资料、用户会话、数据库卷和任何服务密钥不应进入提交历史；GitHub 的推送保护适合作为额外防护。

### 阶段摘要 (第3轮)

已为首次 GitHub 提交准备双任务 CI：后端运行标准库单元测试与语法检查，前端执行可重复的锁文件安装和生产构建。CI 不接触任何真实密钥。

## 本地提交就绪度审计

- 当前仓库位于 `D:\project\course-agent`，分支为 `master`，尚无 Git 提交，也未配置远程仓库。
- 已有 `.env.example`，且 `.env` 已被 `.gitignore` 忽略；示例文件只含变量名与占位值，适合提交。
- 当前 `.gitignore` 尚未忽略 `data/sessions.db`、`data/course.db`、`data/backups/`、`logs/` 和 `.playwright-mcp/`。这些内容含运行数据、日志或本地自动化状态，不能直接提交。
- 当前运行代码并未读取 `data/*.db`、`data/*.json` 作为源代码依赖；Dockerfile 只需要保留一个空 `data/` 目录即可。因此可使用 `data/.gitkeep` 保留目录，忽略动态数据。
- 未发现自动化测试目录；公开仓库的下一步应补充基础测试与 CI，但不要让 CI 使用真实 DeepSeek Key。

## 调研结论

### 建议的首发仓库形态

1. 先创建 **Private** 仓库 `course-agent`，完成安全审计、README 与首个稳定提交后，再决定是否公开。
2. 提交源代码、`postgres/init.sql`、Docker 配置、`.env.example`、启动脚本、README 和无敏感信息的架构文档。
3. 排除 `.env`、`data/` 内的运行数据和上传资料、`logs/`、`.playwright-mcp/`、Python 缓存、前端依赖/构建产物。
4. GitHub 网页端创建**空仓库**（不预建 README、`.gitignore`、许可证），然后从本地创建首个提交并推送到 `main`。

### 建议的提交前检查

```text
git status --short
git check-ignore -v .env data/sessions.db logs/agent.log .playwright-mcp
git diff --cached --name-only
```

只有当最后一项不包含真实资料、数据库、日志和密钥时，才创建首个提交并推送。

### 待确认问题

- 仓库最终是仅用于答辩展示（推荐先 Private）还是需要公开开源？
- 是否愿意将真实课程资料替换为可公开的脱敏演示资料？
- 是否需要我下一步实际补齐 `.gitignore`、README、测试/CI，再由你确认创建远程仓库并推送？

## 来源列表

| 来源 | URL | 访问日期 | 可信度 |
|---|---|---|---|
| GitHub Docs：Adding locally hosted code to GitHub | https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github | 2026-07-25 | 高（官方） |
| GitHub Docs：Ignoring files | https://docs.github.com/en/get-started/git-basics/ignoring-files | 2026-07-25 | 高（官方） |
| GitHub Docs：Creating a new repository | https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository | 2026-07-25 | 高（官方） |
| GitHub Docs：Push protection | https://docs.github.com/en/code-security/concepts/secret-security/push-protection | 2026-07-25 | 高（官方） |
| GitHub Docs：Building and testing Python | https://docs.github.com/en/actions/tutorials/build-and-test-code/python | 2026-07-25 | 高（官方） |
| GitHub Docs：Creating an example workflow | https://docs.github.com/en/actions/tutorials/create-an-example-workflow | 2026-07-25 | 高（官方） |
