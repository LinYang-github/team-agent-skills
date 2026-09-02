# Skill 维护规范

每个 Skill 是独立维护单元。Skill 必须包含有效的 `SKILL.md`，使用小写字母、数字和连字符命名，条件性内容放入 `references/`，并在 `manifest.yaml` 登记版本、状态、责任和依赖。不得包含密钥、Token、个人数据、本机路径或未锁定的在线资源。

## 分支模型

| 分支 | 用途 | 约束 |
| --- | --- | --- |
| `main` | 正式发布基线 | 仅接收发布和紧急修复，不直接推送 |
| `develop` | 日常集成基线 | 工作分支从此创建并通过 Pull Request 合入 |
| `release/*` | 发布准备 | 从 `develop` 创建，完成验证后合入 `main` |
| `hotfix/*` | 正式版本紧急修复 | 从 `main` 创建，修复后同步到 `main` 和 `develop` |

## 分支命名

日常工作分支使用以下格式：

```text
<类型>/<任务号>-<简短描述>
```

允许的类型：

| 类型 | 用途 |
| --- | --- |
| `feature` | 新增能力 |
| `fix` | 普通缺陷修复 |
| `refactor` | 不改变外部行为的结构调整 |
| `docs` | 文档修改 |
| `test` | 测试补充或调整 |
| `chore` | 构建、脚本和仓库维护 |
| `release` | 发布准备 |
| `hotfix` | 正式版本紧急修复 |

有任务系统时使用任务号；没有任务号时直接使用准确的简短描述，例如：

```text
feature/PROJ-123-add-java-skill
fix/PROJ-456-install-script
docs/branch-naming-rules
chore/update-skill-manifest
release/v1.2.0
```

- 类型使用小写 ASCII，描述使用小写 `kebab-case`。
- 不使用空格、中文、个人姓名、Agent 名称、随机字符串或 `tmp`、`new` 等无信息词语。
- 分支只承载一个主题，名称建议不超过 60 个字符，合并后及时删除。

## 开发和提交

```bash
git switch develop
git pull --rebase
git switch -c <类型>/<任务号>-<简短描述>
```

提交信息使用：

```text
<类型>(<范围>): <动作摘要>
```

例如：`新增(code-review): 增加全项目工程审查模板`。一次提交只表达一个可验证意图。

## Pull Request

日常 Pull Request 以 `develop` 为目标分支；正式发布由 `release/*` 或 `develop` 向 `main` 发起。Pull Request 至少说明修改的 Skill、行为或边界影响、依赖同步、实际校验结果和已知限制。合并前必须通过 `./scripts/validate-skills.sh`。

不得绕过 Pull Request 直接推送 `main` 和 `develop`，不得对任何共享分支强制推送。`release/*` 只承载发布准备修改，不得混入下一版本功能；紧急修复完成后必须将 `main` 中的修复同步回 `develop`。
