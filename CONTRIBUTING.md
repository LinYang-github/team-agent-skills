# Skill 维护规范

每个 Skill 是独立维护单元。Skill 必须包含有效的 `SKILL.md`，使用小写字母、数字和连字符命名，条件性内容放入 `references/`，并在 `manifest.yaml` 登记版本、状态、责任和依赖。不得包含密钥、Token、个人数据、本机路径或未锁定的在线资源。

## 分支和提交

```bash
git switch main
git pull --rebase
git switch -c feature/<任务号>-<简短描述>
```

提交信息使用：

```text
<类型>(<范围>): <动作摘要>
```

例如：`新增(code-review): 增加全项目工程审查模板`。一次提交只表达一个可验证意图。

## Pull Request

Pull Request 至少说明修改的 Skill、行为或边界影响、依赖同步、实际校验结果和已知限制。合并前必须通过 `./scripts/validate-skills.sh`。不得直接推送 `main`，不得对共享分支强制推送。
