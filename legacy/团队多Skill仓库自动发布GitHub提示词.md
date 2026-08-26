# 团队多 Skill 仓库自动发布 GitHub 提示词

> 适用场景：当前本地目录中已经存在多个开发完成的 Skill，希望由 Agent 自动扫描、为每个 Skill 生成独立安装脚本，并统一发布到一个 GitHub 私有仓库。
>
> 最终目标：**一个 GitHub 仓库管理多个 Skill；每个 Skill 都是独立安装单元；每个 Skill 都自带 Codex / Claude / Grok × macOS / Windows 共 6 个安装脚本。**

---

## 可直接复制执行的提示词

你现在是一个 **AI Agent Skill 团队仓库发布助手**。

当前工作目录是一个团队 Skill 仓库根目录，其中已经存在一个或多个编写完成的 Skill。

你的任务不是给我教程，而是**直接在当前项目中完成整理、脚本生成、GitHub 仓库创建和首次发布**。

整体流程：

```text
扫描多个 Skill
    ↓
确认每个 Skill 的 SKILL.md
    ↓
为每个 Skill 分别生成 6 个安装脚本
    ↓
校验安装脚本
    ↓
初始化 / 更新 Git
    ↓
创建一个 GitHub Private Repository
    ↓
提交所有 Skill 和安装脚本
    ↓
Push main
    ↓
验证最终产物
```

除 GitHub 官方登录授权等必须由用户参与的步骤外，不要逐条向我询问确认，直接执行。

---

# 一、目标仓库结构

当前目录是**团队 Skill 仓库根目录**。

期望结构：

```text
team-agent-skills/
├── README.md
├── .gitignore
└── skills/
    ├── skill-a/
    │   ├── SKILL.md
    │   ├── references/
    │   ├── assets/
    │   ├── tests/
    │   └── scripts/
    │       ├── install-codex-macos.sh
    │       ├── install-codex-windows.ps1
    │       ├── install-claude-macos.sh
    │       ├── install-claude-windows.ps1
    │       ├── install-grok-macos.sh
    │       └── install-grok-windows.ps1
    │
    ├── skill-b/
    │   ├── SKILL.md
    │   └── scripts/
    │       ├── install-codex-macos.sh
    │       ├── install-codex-windows.ps1
    │       ├── install-claude-macos.sh
    │       ├── install-claude-windows.ps1
    │       ├── install-grok-macos.sh
    │       └── install-grok-windows.ps1
    │
    └── skill-c/
        ├── SKILL.md
        └── scripts/
            ├── install-codex-macos.sh
            ├── install-codex-windows.ps1
            ├── install-claude-macos.sh
            ├── install-claude-windows.ps1
            ├── install-grok-macos.sh
            └── install-grok-windows.ps1
```

注意：

- 一个 GitHub Repository 中允许存在多个 Skill。
- 每个 Skill 必须是一个独立目录。
- 每个 Skill 必须至少包含 `SKILL.md`。
- 每个 Skill 的安装脚本放在它自己的 `scripts/` 目录。
- **禁止把 6 个安装脚本只放在仓库根目录统一管理。**
- **禁止采用“一个 Skill 一个 GitHub Repository”的方式。**

---

# 二、扫描并识别所有 Skill

扫描：

```text
skills/*/SKILL.md
```

将所有符合条件的目录识别为 Skill。

例如：

```text
skills/
├── model-validation-judgement/
│   └── SKILL.md
├── architecture-design/
│   └── SKILL.md
└── frontend-design/
    └── SKILL.md
```

应识别出：

```text
model-validation-judgement
architecture-design
frontend-design
```

Skill 名称优先级：

1. 优先读取 `SKILL.md` Frontmatter 中的 `name`；
2. 如果没有 `name`，使用 Skill 目录名。

如果：

```text
skills/
```

不存在，或者没有找到任何：

```text
skills/*/SKILL.md
```

停止操作，并明确告诉我没有识别到可发布的 Skill。

不得擅自把其他普通目录当作 Skill。

---

# 三、为每个 Skill 生成 6 个安装脚本

对扫描到的**每一个 Skill**，都必须在：

```text
skills/<skill-name>/scripts/
```

生成：

```text
install-codex-macos.sh
install-codex-windows.ps1
install-claude-macos.sh
install-claude-windows.ps1
install-grok-macos.sh
install-grok-windows.ps1
```

例如当前识别到 3 个 Skill：

```text
skill-a
skill-b
skill-c
```

最终必须生成：

```text
3 × 6 = 18 个安装脚本
```

如果识别到 5 个 Skill：

```text
5 × 6 = 30 个安装脚本
```

所有 Skill 都必须生成，不得遗漏。

---

# 四、每个安装脚本只安装自己所在的 Skill

这是强制规则。

例如：

```text
team-agent-skills/
└── skills/
    └── model-validation-judgement/
        ├── SKILL.md
        └── scripts/
            └── install-codex-macos.sh
```

执行：

```bash
skills/model-validation-judgement/scripts/install-codex-macos.sh
```

只能安装：

```text
model-validation-judgement
```

不得：

- 扫描 `skills/*`；
- 安装其他 Skill；
- 修改其他 Skill 的安装状态；
- 顺便安装 Claude；
- 顺便安装 Grok。

安装脚本必须通过**自身路径**定位 Skill 根目录。

逻辑等价于：

```text
SCRIPT_DIR
    ↓
父目录
    ↓
SKILL_DIR
    ↓
SKILL_NAME
```

例如：

```text
SCRIPT_DIR =
/workspace/team-agent-skills/skills/model-validation-judgement/scripts

SKILL_DIR =
/workspace/team-agent-skills/skills/model-validation-judgement

SKILL_NAME =
model-validation-judgement
```

然后将：

```text
SKILL_DIR
```

链接到目标 Agent 的 Skill 目录。

---

# 五、Codex 安装规则

Codex 用户级 Skill 目录：

macOS：

```text
~/.agents/skills
```

Windows：

```text
%USERPROFILE%\.agents\skills
```

例如：

```text
~/.agents/skills/model-validation-judgement
```

应指向：

```text
<repo>/skills/model-validation-judgement
```

Codex 安装脚本只允许处理：

```text
~/.agents/skills/<当前skill-name>
```

---

# 六、Claude 安装规则

Claude 用户级 Skill 目录：

macOS：

```text
~/.claude/skills
```

Windows：

```text
%USERPROFILE%\.claude\skills
```

例如：

```text
~/.claude/skills/model-validation-judgement
```

应指向：

```text
<repo>/skills/model-validation-judgement
```

Claude 安装脚本只允许处理：

```text
~/.claude/skills/<当前skill-name>
```

---

# 七、Grok 安装规则

Grok 用户级 Skill 目录：

macOS：

```text
~/.grok/skills
```

Windows：

```text
%USERPROFILE%\.grok\skills
```

例如：

```text
~/.grok/skills/model-validation-judgement
```

应指向：

```text
<repo>/skills/model-validation-judgement
```

Grok 安装脚本只允许处理：

```text
~/.grok/skills/<当前skill-name>
```

---

# 八、macOS 安装脚本要求

三个 macOS 脚本：

```text
install-codex-macos.sh
install-claude-macos.sh
install-grok-macos.sh
```

统一使用 Bash。

必须：

1. 使用：

```bash
set -euo pipefail
```

2. 根据脚本自身位置确定：

```text
SCRIPT_DIR
SKILL_DIR
SKILL_NAME
```

3. 自动创建 Agent 的 Skill 根目录。

4. 使用 Symbolic Link。

5. 不复制 Skill 文件。

6. 链接整个当前 Skill 根目录：

```text
skills/<skill-name>
```

而不是只链接 `SKILL.md`。

7. 支持重复执行。

8. 如果目标已经正确指向当前 Skill：

```text
[OK]
```

并正常退出。

9. 如果存在同名真实目录或指向其他位置的链接：

默认：

```text
[SKIP]
```

不得直接覆盖。

10. 支持：

```bash
--force
```

11. `--force` 模式下，先将原目标备份为：

```text
<skill-name>.bak.<yyyyMMdd-HHmmss>
```

再建立链接。

12. 不得删除未备份的已有 Skill。

13. 每个脚本只允许修改自己的目标 Agent 路径。

例如 Codex 脚本不得修改：

```text
~/.claude/skills
~/.grok/skills
```

---

# 九、Windows 安装脚本要求

三个 Windows 脚本：

```text
install-codex-windows.ps1
install-claude-windows.ps1
install-grok-windows.ps1
```

统一使用 PowerShell。

必须：

1. 根据 `$PSScriptRoot` 定位当前 Skill 根目录。

2. 自动获取：

```text
SKILL_DIR
SKILL_NAME
```

3. 自动创建 Agent 的 Skill 根目录。

4. 使用：

```text
NTFS Directory Junction
```

5. 不复制 Skill 文件。

6. 尽量避免要求管理员权限或 Developer Mode。

7. 支持重复执行。

8. 如果目标已经正确链接当前 Skill：

```text
[OK]
```

9. 存在冲突时默认：

```text
[SKIP]
```

10. 支持参数：

```powershell
-Force
```

11. `-Force` 时先备份：

```text
<skill-name>.bak.<yyyyMMdd-HHmmss>
```

再创建 Junction。

12. 不得无备份删除已有 Skill。

13. Codex、Claude、Grok 三类脚本必须完全隔离。

---

# 十、脚本注释要求

每个脚本顶部必须写明：

```text
脚本用途
目标 Agent
当前脚本只安装自己所在的 Skill
目标 Skill 目录
普通安装方法
强制安装方法
```

例如 macOS：

```bash
./scripts/install-codex-macos.sh
./scripts/install-codex-macos.sh --force
```

Windows：

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\install-codex-windows.ps1

powershell -ExecutionPolicy Bypass `
  -File .\scripts\install-codex-windows.ps1 `
  -Force
```

---

# 十一、校验所有生成脚本

生成完后，重新扫描所有 Skill。

对于每个：

```text
skills/<skill-name>
```

检查必须存在：

```text
SKILL.md

scripts/install-codex-macos.sh
scripts/install-codex-windows.ps1

scripts/install-claude-macos.sh
scripts/install-claude-windows.ps1

scripts/install-grok-macos.sh
scripts/install-grok-windows.ps1
```

输出统计，例如：

```text
识别 Skill 数量：3
理论脚本数量：18
实际脚本数量：18
缺失脚本：0
```

如果数量不一致：

不得继续发布。

必须先补齐。

---

# 十二、脚本基础语法校验

不要为了测试安装脚本而真正修改我的：

```text
~/.agents/skills
~/.claude/skills
~/.grok/skills
```

只做非侵入式检查。

对 macOS Shell 脚本执行：

```bash
bash -n <script>
```

逐个检查全部 `.sh`。

例如：

```bash
find skills -path "*/scripts/install-*-macos.sh" -type f -print0 \
  | xargs -0 -n1 bash -n
```

PowerShell 脚本进行静态语法检查。

如果当前环境存在 `pwsh`，可以使用 PowerShell Parser 或等效非执行方式检查语法。

不得为了验证脚本而真正创建 Symlink / Junction。

---

# 十三、必要的 Git / GitHub 检查

不要进行复杂的 Git 环境诊断。

只需要检查：

```bash
git --version
gh --version
gh auth status
```

如果 Git 不存在：

停止，并告诉我缺少 Git。

如果 GitHub CLI 不存在：

停止，并告诉我缺少 `gh`。

如果 GitHub 未登录：

执行：

```bash
gh auth login
```

让我完成 GitHub 官方授权。

授权后继续。

不需要进行大量无关的 Git 配置检查。

---

# 十四、基础敏感文件保护

提交前只做必要检查。

检查：

```text
.env
.env.*
*.pem
*.key
*.p12
*.pfx
id_rsa
id_ed25519
credentials*
secrets*
```

如果存在明显不应该提交的文件：

补充：

```text
.gitignore
```

不要删除用户原始文件。

不要进行复杂的全文 Secret 扫描。

---

# 十五、初始化或更新 Git

如果当前仓库还没有 Git：

```bash
git init
git branch -M main
```

然后：

```bash
git add .
git status
git commit -m "chore: initialize team skill repository"
```

如果当前已经是 Git Repository：

不要破坏已有历史。

检查：

```bash
git status
```

如果本次新增或修改了安装脚本：

```bash
git add .
git commit -m "chore: add skill installer scripts"
```

如果没有任何变更：

不要创建空 Commit。

禁止：

```bash
git reset --hard
git clean -fd
```

---

# 十六、创建一个 GitHub Repository

整个：

```text
team-agent-skills/
```

只创建**一个 GitHub Repository**。

禁止：

```text
skill-a → repo-a
skill-b → repo-b
skill-c → repo-c
```

正确形式：

```text
GitHub Repository
└── team-agent-skills
    └── skills
        ├── skill-a
        ├── skill-b
        └── skill-c
```

Repository 名称默认使用当前仓库根目录名称。

例如：

```text
team-agent-skills
```

默认：

```text
Visibility = Private
Branch = main
Remote = origin
```

---

# 十七、创建和推送 GitHub Repository

首先检查：

```bash
git remote -v
```

如果没有 `origin`：

使用：

```bash
gh repo create <repo-name> \
  --private \
  --source=. \
  --remote=origin \
  --push
```

如果已经存在 GitHub `origin`：

不要重新创建 Repository。

正常：

```bash
git push -u origin main
```

如果 `origin` 明显指向其他无关仓库：

停止操作并告诉我。

不得自动删除或重写现有 `origin`。

---

# 十八、禁止危险 Git 操作

严禁自动执行：

```bash
git push --force
git push -f
git reset --hard
git clean -fd
```

不得为了完成发布而覆盖团队已有 Git 历史。

如果出现实际远程冲突：

停止并说明问题。

---

# 十九、README 更新

如果仓库根目录不存在：

```text
README.md
```

创建一个简洁的 README。

如果已经存在：

不要覆盖已有主要内容，可以补充一个：

```text
Skill 安装
```

章节。

README 至少列出当前识别到的所有 Skill：

```text
- model-validation-judgement
- architecture-design
- frontend-design
```

并说明：

每个 Skill 都有独立安装脚本。

例如安装：

```bash
cd skills/model-validation-judgement

./scripts/install-codex-macos.sh
```

Windows：

```powershell
cd skills\model-validation-judgement

powershell -ExecutionPolicy Bypass `
  -File .\scripts\install-codex-windows.ps1
```

同时说明：

```text
修改已有 Skill 后：
git pull 即可获取最新内容。

新增 Skill 后：
git pull 后，执行新 Skill 自己目录下的安装脚本即可。
```

---

# 二十、最终产物强制检查

最终 GitHub Repository 必须类似：

```text
team-agent-skills/
├── README.md
├── .gitignore
└── skills/
    ├── skill-a/
    │   ├── SKILL.md
    │   └── scripts/
    │       ├── install-codex-macos.sh
    │       ├── install-codex-windows.ps1
    │       ├── install-claude-macos.sh
    │       ├── install-claude-windows.ps1
    │       ├── install-grok-macos.sh
    │       └── install-grok-windows.ps1
    │
    ├── skill-b/
    │   ├── SKILL.md
    │   └── scripts/
    │       ├── install-codex-macos.sh
    │       ├── install-codex-windows.ps1
    │       ├── install-claude-macos.sh
    │       ├── install-claude-windows.ps1
    │       ├── install-grok-macos.sh
    │       └── install-grok-windows.ps1
    │
    └── skill-c/
        ├── SKILL.md
        └── scripts/
            ├── install-codex-macos.sh
            ├── install-codex-windows.ps1
            ├── install-claude-macos.sh
            ├── install-claude-windows.ps1
            ├── install-grok-macos.sh
            └── install-grok-windows.ps1
```

对于识别到的每一个 Skill：

```text
必须有 1 个 SKILL.md
必须有 6 个安装脚本
```

不得只给部分 Skill 生成脚本。

---

# 二十一、最终验证

执行：

```bash
git status
git remote -v
git branch --show-current
git log -1 --oneline
```

同时确认：

```text
GitHub Repository：1 个
Skill 数量：N
安装脚本数量：N × 6
Branch：main
Remote：origin
Visibility：Private
```

最终输出格式：

```text
团队 Skill 仓库发布完成

Repository：
GitHub：
Visibility：Private
Branch：main
Remote：origin

识别 Skill 数量：N

Skill 列表：
1. xxx
2. xxx
3. xxx

安装脚本：
Codex macOS：N
Codex Windows：N
Claude macOS：N
Claude Windows：N
Grok macOS：N
Grok Windows：N

安装脚本总数：N × 6

Latest Commit：
Working Tree：

团队成员使用方式：

git clone <repository>

进入具体 Skill：

cd skills/<skill-name>

然后根据使用的 Agent 和操作系统执行对应安装脚本。
```

如果任一步骤失败：

不得输出：

```text
发布完成
```

必须输出：

```text
失败步骤：
失败原因：
已完成内容：
未完成内容：
```

---

# 二十二、最终原则

整个任务必须始终遵守以下规则：

1. **一个 GitHub Repository 管理多个 Skill。**
2. **Skill 必须位于 `skills/<skill-name>/`。**
3. **每个 Skill 都必须有自己的 6 个安装脚本。**
4. **每个脚本只安装自己所在的 Skill。**
5. **不得扫描并批量安装其他 Skill。**
6. **Codex、Claude、Grok 安装脚本完全独立。**
7. **macOS 使用 Symbolic Link。**
8. **Windows 使用 NTFS Junction。**
9. **已有 Skill 默认不覆盖，强制模式必须先备份。**
10. **GitHub Repository 默认 Private。**
11. **禁止 Force Push。**
12. **最终必须验证：Skill 数量 × 6 = 安装脚本总数。**
