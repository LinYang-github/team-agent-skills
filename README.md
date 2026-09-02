# 团队 Agent Skills

本仓库统一维护团队可复用的 Agent Skills。Skill 的正式版本位于 `skills/`，通过 Git 进行协作和版本追踪。

## 当前 Skill

| Skill | 用途 | 状态 |
| --- | --- | --- |
| `common-coding-standards` | 跨语言通用编码、文档、Git、测试和交付规范 | active |
| `code-review` | 代码变更、全项目工程和部署交付审查 | active |
| `cpp-coding-standard` | C++ 工程、语言、构建、资源和工具链规范 | active |
| `frontend-coding-standard` | Vue/TypeScript 企业级前端工程规范 | active |
| `go-coding-standards` | Go 服务、并发、配置、错误和测试规范 | active |
| `ui-ux-standards` | 桌面端 UI/UX 视觉和交互规范 | active |
| `playwright-tester` | Playwright 测试生成规范 | active |

开源或外部来源的 Skill 不纳入本仓库的内部版本治理。

## 安装

安装全部内部 Skill：

```bash
./scripts/install-codex-macos.sh
```

强制安装全部内部 Skill：

```bash
./scripts/install-codex-macos.sh --force
```

Claude 和 Grok 使用对应的安装脚本。Windows 使用同名 `.ps1` 脚本。默认安装不会覆盖本机已有同名 Skill；确认采用团队版本时显式添加 `--force` 或 `-Force`，脚本会先备份原目录。

## 本地质量门禁

仓库提供统一的本地检查器和 `pre-commit`、`commit-msg`、`pre-push` 三类 Git Hook。macOS/Linux 执行：

```bash
./scripts/manage-git-hooks.sh
```

Windows PowerShell 执行：

```powershell
./scripts/manage-git-hooks.ps1
```

Hook 只负责触发，强制规则和项目检查命令统一维护在 `quality-gates.json`。详细说明见 [本地质量门禁](docs/本地质量门禁.md)。

## Skill 测评

各 Skill 的 `evals/` 目录保存基于 `skill-up` 的行为评测。单项复测命令：

```bash
skill-up run skills/<skill-name>/evals/eval.yaml --baseline --iteration 3
```

当前结果、评分口径和后续整改顺序见 [团队 Skill 测评报告](docs/团队Skill测评报告.md)。

## 更新

```bash
git pull --rebase
```

安装器当前按 Agent 批量安装全部内部 Skill，符号链接/Junction 指向仓库目录。更新仓库后即可使用新内容；新增 Skill 后再次执行对应 Agent 的安装脚本即可。

## 参与维护

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [docs/使用指南.md](docs/使用指南.md)，并启用本地质量门禁。Skill 变更必须经过校验和 Pull Request，不直接修改共享分支。

日常修改从 `develop` 创建类型化短分支，并通过 Pull Request 合回 `develop`；分支名称使用 `feature/*`、`fix/*`、`refactor/*`、`docs/*`、`test/*` 或 `chore/*` 等约定前缀。
