# 团队 Skill 使用与维护手册（精简版）

## 1. 适用范围

本手册面向已经获得团队 Skill GitHub 仓库权限的成员。

团队 Skill 统一保存在一个 GitHub 仓库中：

```text
team-agent-skills/
└── skills/
    ├── skill-a/
    ├── skill-b/
    └── skill-c/
```

每个 Skill 都是独立安装单元，并自带 Codex、Claude、Grok 对应的 macOS / Windows 安装脚本。

---

## 2. 第一次使用

### 2.1 克隆仓库

```bash
git clone <团队 Skill 仓库地址>
cd team-agent-skills
```

### 2.2 进入需要使用的 Skill

例如：

```bash
cd skills/model-validation-judgement
```

---

## 3. 安装 Skill

只执行自己需要的 Agent 脚本。

### macOS

#### Codex

```bash
chmod +x scripts/install-codex-macos.sh
./scripts/install-codex-macos.sh
```

#### Claude

```bash
chmod +x scripts/install-claude-macos.sh
./scripts/install-claude-macos.sh
```

#### Grok

```bash
chmod +x scripts/install-grok-macos.sh
./scripts/install-grok-macos.sh
```

### Windows

#### Codex

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\install-codex-windows.ps1
```

#### Claude

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\install-claude-windows.ps1
```

#### Grok

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\install-grok-windows.ps1
```

安装脚本只会安装当前 Skill，不会影响仓库中的其他 Skill。

---

## 4. Skill 如何生效

安装脚本不会复制 Skill，而是把 Agent 的 Skill 目录链接到当前 Git 仓库中的 Skill。

例如 Codex：

```text
~/.agents/skills/model-validation-judgement
                    │
                    ▼
team-agent-skills/skills/model-validation-judgement
```

因此以后仓库内容更新后，不需要重新复制文件。

---

## 5. 日常更新

获取团队最新 Skill：

```bash
cd team-agent-skills
git pull --rebase
```

如果只是修改了已有 Skill，执行完：

```bash
git pull --rebase
```

即可。

### 仓库新增了一个 Skill

先更新：

```bash
git pull --rebase
```

然后进入新 Skill：

```bash
cd skills/<new-skill>
```

再执行对应 Agent 的安装脚本一次。

---

## 6. 修改 Skill

不要直接在 `main` 上开发。

首先同步：

```bash
git switch main
git pull --rebase
```

创建自己的分支：

```bash
git switch -c feat/<修改内容>
```

例如：

```bash
git switch -c feat/improve-validation-rules
```

修改对应：

```text
skills/<skill-name>/SKILL.md
```

或：

```text
references/
scripts/
tests/
```

完成后检查：

```bash
git status
git diff
```

提交：

```bash
git add .
git commit -m "feat: improve validation rules"
```

推送：

```bash
git push -u origin feat/improve-validation-rules
```

然后在 GitHub 创建 Pull Request，Review 通过后合并到 `main`。

---

## 7. 提交规范

建议使用：

```text
feat: 新增能力
fix: 修复问题
docs: 修改文档
refactor: 重构 Skill
test: 增加测试
chore: 调整脚本或工程配置
```

例如：

```text
feat: add evidence matching rules
fix: correct pending-review judgement
docs: update skill usage
```

---

## 8. 多人同时修改

如果其他成员已经更新了 `main`，自己的分支在提交前建议同步：

```bash
git fetch origin
git rebase origin/main
```

有冲突时人工解决后：

```bash
git add <冲突文件>
git rebase --continue
```

然后正常推送。

禁止对 `main` 使用：

```bash
git push --force
```

---

## 9. 已有同名 Skill

如果执行安装脚本时本地已经存在同名 Skill，脚本默认不会覆盖。

确认要使用团队仓库版本时：

### macOS

```bash
./scripts/install-codex-macos.sh --force
```

### Windows

```powershell
.\scripts\install-codex-windows.ps1 -Force
```

脚本会先备份原 Skill，再建立新的链接。

Claude、Grok 使用方式相同，只需替换对应脚本名称。

---

## 10. 推荐日常流程

### 只使用 Skill

```text
git pull
↓
直接使用
```

### 使用新增加的 Skill

```text
git pull
↓
进入新 Skill
↓
执行对应 Agent 安装脚本
↓
使用
```

### 修改 Skill

```text
更新 main
↓
创建 Feature Branch
↓
修改 Skill
↓
Commit
↓
Push
↓
Pull Request
↓
Review
↓
Merge
```

---

## 11. 团队约定

团队成员统一遵守：

1. GitHub 仓库是 Skill 的正式版本源。
2. 不通过复制文件的方式维护 Skill。
3. 已安装 Skill 的日常更新使用 `git pull --rebase`。
4. 新增 Skill 需要单独执行一次对应安装脚本。
5. 修改 Skill 使用独立分支。
6. 合并到 `main` 前走 Pull Request。
7. 不直接覆盖其他成员的修改。
8. 禁止 Force Push `main`。
9. API Key、Token、密码等敏感信息不得提交到 Skill 仓库。
10. 修改 Skill 后建议验证原有使用场景，避免行为退化。
