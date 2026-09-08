# 2026-09-07：MyBatis 规范溯源 A/B 记录

## 目的

验证显式调用 `java-coding-standard` 后，Agent 能否在修复 MyBatis SQL 注入时引用实际存在的内部规范文件。

## 方法

- 工具：`skill-up 0.10.0`；引擎：已认证的 Codex 默认模型。
- 用例：`reference-traceability-sql`。
- 对照：相同输入分别以 `with_skill`、`without_skill` 运行。
- 判定：输出必须包含 `强制`、`#{name}`、`references/05-mysql-database.md`。
- 输入要求显式使用 `java-coding-standard` Skill，并审查 MyBatis XML 中 `${name}` 拼接参数的风险。

## 结果

| 重复 | with_skill | without_skill |
| --- | --- | --- |
| iteration-13 | PASS | FAIL |
| iteration-14 | PASS | FAIL |
| iteration-15 | PASS | FAIL |
| 汇总 | 3/3 | 0/3 |

有 Skill 时，答案稳定使用 `#{name}` 并引用 `references/05-mysql-database.md`。无 Skill 时，答案能给出同样的参数化修复，但引用了不存在的路径，因此未通过。

这证明的是「显式调用时的规范可溯源能力」提升，不代表通用 Java 编码正确性整体提升。JDK 兼容、动态排序、可空契约、框架适配等案例继续作为回归门禁。

## 原始工件

- `iteration-13-report.html` 与 `iteration-13-result.json`
- `iteration-14-report.html` 与 `iteration-14-result.json`
- `iteration-15-report.html` 与 `iteration-15-result.json`

复跑：

```bash
skill-up run evals/eval.yaml --include-case-name reference-traceability-sql --parallelism 2 --format html
```
