# team-standards：团队 Agent 规范插件

让 AI 编码 Agent 按团队规范写代码、建分支、写提交信息。一个插件包含三部分：

| 组成 | 作用 | 生效方式 |
| --- | --- | --- |
| 编码规范技能（`skills/`） | 通用、各语言、代码审查、UI/UX、Playwright 等规范 | 安装插件后 Agent 按任务自动选用 |
| Agent 钩子（`hooks/`） | Agent 执行建分支、`git commit -m`、推送受保护分支前先预检，不合规直接拦下 | 插件安装并**信任钩子**后生效 |
| 项目 Git 钩子 | 在你的项目里检查实际的提交信息和推送分支，Agent 钩子没生效时兜底 | 每个项目**手动启用一次** |

支持的客户端：Codex、ZCode、dsh（含 HuiMate）。Claude、Grok 暂时用[备用安装脚本](#备用安装方式)。

> 插件名 `team-standards`，市场名 `team-agent-skills`，默认跟随 `develop` 分支。下文示例使用 GitHub 地址，内网使用时替换为团队仓库地址。

## 前置依赖

安装前先确认本机具备以下工具。缺少时插件不会报安装错误，但对应功能会**静默失效**，所以请逐项检查。

| 依赖 | 谁需要 | 缺少时会怎样 | 检查命令 |
| --- | --- | --- | --- |
| Git，并能访问团队仓库（凭据或 SSH key 已配置） | 所有人 | 无法安装和更新插件；安装过程不会弹出登录框 | `git ls-remote <仓库地址>` |
| POSIX shell：macOS/Linux 自带；Windows 需要 [Git for Windows](https://git-scm.com/download/win) 的 Git Bash，钩子入口另需系统自带的 Windows PowerShell | 所有人 | 钩子无法运行 | `sh -c 'echo ok'`；Windows 另查 `powershell.exe -NoProfile -Command "echo ok"` |
| Perl 及核心模块 `JSON::PP`：macOS/Linux 通常自带；Git for Windows 自带 | 使用 Agent 钩子的人 | Agent 预检**直接放行**，只在 stderr 打一行警告；仅剩项目 Git 钩子兜底 | `perl -MJSON::PP -e 'print "ok\n"'` |
| UTF-8 locale | 所有人 | 钩子报错退出，无法按字符校验中文提交信息 | `printf '中' \| LC_ALL=C.UTF-8 wc -m`（输出 `1`） |
| Python 3 | 只有本仓库维护者 | 无法运行全量质量门禁和规则生成；**日常使用不需要** | `python3 --version` |

## 快速开始

### 1. 安装插件

**Codex**

```bash
codex plugin marketplace add https://github.com/LinYang-github/team-agent-skills.git --ref develop
codex plugin add team-standards@team-agent-skills
```

新建会话时会提示 “N hooks need review”，选择 **Trust all and continue**。不信任或使用无头 `codex exec` 时，Agent 钩子不会运行。

**ZCode**

```bash
zcode plugins marketplace add "https://github.com/LinYang-github/team-agent-skills.git#develop"
zcode plugins install team-standards@team-agent-skills
zcode plugins enable team-standards@team-agent-skills
```

启用后到 设置 → Hooks 确认已出现 `Bash` matcher 的钩子，再新建会话。

**dsh**（`<p>` 换成实际 profile 名，例如 `web`）

```bash
dsh plugin --profile <p> add "git+https://github.com/LinYang-github/team-agent-skills.git#develop"
```

dsh 还需要在 `dsh-skill-filesystem` 的 `customSkillDirs` 中加入包内 `skills` 目录的绝对路径。这种 pnpm 安装方式不会运行 Agent 钩子，必须做第 2 步。HuiMate 从插件市场安装时会通过 `dsh-hooks-claude-code` 桥接运行 Agent 钩子，需 0.1.4 及以上版本。详见 [插件安装与更新 · dsh](docs/插件安装与更新.md#dsh)。

### 2. 在项目中启用 Git 钩子

每个要受规范约束的项目执行一次（Windows 在 Git Bash 中运行）：

```bash
sh <插件目录>/hooks/lib/install-git-hooks.sh "/项目仓库绝对路径"
```

不知道插件目录在哪：在项目里新建一次 Codex / ZCode 会话，插件会输出一行包含完整路径的启用命令。项目已使用 husky 或设置了 `core.hooksPath` 时，安装器会拒绝覆盖并退出，需要由项目维护者手动集成。

### 3. 验证是否生效

| 检查项 | 方法 | 预期结果 |
| --- | --- | --- |
| 技能已加载 | 新建会话，问 Agent “列出 team-standards 提供的技能” | 能说出 `common-coding-standards` 等技能 |
| Agent 钩子已信任 | Codex 启动时无 “need review” 提示；ZCode 设置 → Hooks 中可见 | 已信任 / 已启用 |
| Agent 预检依赖 | `perl -MJSON::PP -e 'print "ok\n"'` | 输出 `ok` |
| 项目 Git 钩子已启用 | 在项目里执行 `cat "$(git rev-parse --git-path hooks)/.team-standards-version"` | 输出插件版本号，例如 `0.1.4` |

## 包含的技能

| 技能 | 什么时候用 |
| --- | --- |
| `common-coding-standards` | 任何项目的通用规范：命名、注释、异常、日志、配置、安全、测试、依赖、提交和审查 |
| `code-review` | 审查未提交修改、提交范围、分支差异，以及构建、部署、迁移和回滚方案 |
| `cpp-coding-standard` | C++ 工程：构建、头文件、资源所有权、并发、API/ABI、存量 SDK 二次开发 |
| `csharp-coding-standard` | C#/.NET 工程：项目结构、生命周期、异步与并发、API 版本 |
| `java-coding-standard` | Java 工程：并发、异常、安全、MySQL、Maven/Gradle、Spring |
| `go-coding-standards` | Go 服务：包结构、错误处理、配置启动、有界并发、API 契约 |
| `python-coding-standard` | Python 工程：项目结构、类型、并发与异步、工具链 |
| `frontend-coding-standard` | 企业级前端，默认 Vue 3 + TypeScript：架构、路由、状态、接口、构建、宿主集成 |
| `ui-ux-standards` | 桌面端界面：新页面设计、既有页面改造、组件一致性和视觉回归 |
| `playwright-tester` | 按 Vue Router 路由访问真实页面，生成 Playwright spec 和测试用例文档 |

各技能的版本、状态和依赖关系登记在 [manifest.yaml](manifest.yaml)。

## 更新

| 客户端 | 更新方式 |
| --- | --- |
| Codex | 每次启动会话自动更新市场和插件。更新后钩子会变成 “Modified since last trusted”，需要**重新信任** |
| ZCode | `zcode plugins marketplace update`，再 `zcode plugins update team-standards@team-agent-skills`，然后新建会话 |
| dsh | `dsh plugin --profile <p> update team-standards` |

已启用 Git 钩子的项目，会在下一次 Codex / ZCode 会话启动时自动升级钩子，不会降级。dsh 用户更新后需要重新运行第 2 步的安装命令。

## 常见问题

**Codex 显示 “Modified since last trusted - review required”**
插件每次更新（哪怕只改了一份技能文档）都需要重新信任钩子。选择 Trust all and continue 即可。

**Agent 钩子没拦住不合规的提交信息**
先检查：钩子是否已信任；本机是否有 Perl（见[前置依赖](#前置依赖)）；是否用了 `codex exec` 等无头模式。这些情况下由项目 Git 钩子兜底，确认第 2 步已完成。

**确实需要直接推送 `main` / `develop`**
默认禁止，应走合并请求。已获授权的例外可在环境中设置 `QUALITY_GATE_ALLOW_PROTECTED_PUSH=1`。

**安装器提示已有 `core.hooksPath` 或同名钩子**
项目已有其他门禁（例如 husky）。安装器不会覆盖，请勿为此删除现有门禁，由项目维护者把检查手动集成到原流程中。

**Windows 上钩子报 Permission denied 或找不到 bash**
确认已安装 Git for Windows；不要使用 WSL 的 bash。脚本需要保持 LF 行尾。

更多协议细节和排障见 [插件安装与更新](docs/插件安装与更新.md)。

## 卸载

先在每个启用过的项目里卸载 Git 钩子，再删除客户端插件。顺序不能反：只删插件时，已复制到项目的 Git 钩子会继续生效。

```bash
sh <插件目录>/hooks/lib/install-git-hooks.sh --uninstall "/项目仓库绝对路径"
codex plugin remove team-standards@team-agent-skills
```

ZCode 在 设置 → 插件 中卸载；dsh 执行 `dsh plugin --profile <p> remove team-standards`，并从 `customSkillDirs` 删除对应路径。

## 备用安装方式

暂时不能使用插件的环境（包括 Claude、Grok），可以克隆本仓库后用脚本把技能链接到 Agent 的技能目录：

```bash
git clone https://github.com/LinYang-github/team-agent-skills.git
cd team-agent-skills
./scripts/install-codex-macos.sh      # 或 install-claude-macos.sh / install-grok-macos.sh
```

Windows 使用同名 `.ps1` 脚本。默认不覆盖本机已有同名技能，确认使用团队版本时加 `--force`（Windows 为 `-Force`），脚本会先备份原目录。之后 `git pull --rebase` 即可更新。

这种方式**只安装技能**，不包含 Agent 钩子。需要另外完成[第 2 步](#2-在项目中启用-git-钩子)，并避免与插件同时安装造成同名技能重复加载。安装目录等细节见 [使用指南](docs/使用指南.md)。

## 参与维护

修改本仓库前请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，里面包括分支和提交规范、维护者环境、质量门禁、技能测评和插件发版。

| 文档 | 内容 |
| --- | --- |
| [插件安装与更新](docs/插件安装与更新.md) | 各客户端安装细节、钩子协议、Windows 兼容、排障 |
| [使用指南](docs/使用指南.md) | 备用安装脚本的安装目录和更新方式 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 命名、分支、提交、Pull Request 和维护者环境 |
| [维护流程](docs/维护流程.md) | 新增、修改技能和版本状态 |
| [发布流程](docs/发布流程.md) | 日常合并与正式发布 |
| [本地质量门禁](docs/本地质量门禁.md) | 本仓库的全量 Git Hook 检查 |
| [团队 Skill 测评报告](docs/团队Skill测评报告.md) | 各技能的行为评测结果 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更记录 |
