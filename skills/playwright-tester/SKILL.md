---
name: playwright-tester
description: 按 Vue Router 路由顺序访问真实业务页面，记录安全点击和运行时结果并生成版本化 Playwright spec 与 test_case Markdown。
license: MIT
metadata:
  author: lackeyjb
  version: "2.0.0"
allowed-tools: Bash(node:*) Bash(npx:*) Bash(npm:*) Read Write
---

# Playwright 浏览器捕获技能

本技能只负责 `capture`：根据前端源码发现静态路由，使用 Playwright 真实访问页面，
记录页面实际可见的安全点击、导航和 Dialog 状态，生成 `.spec.js/.spec.ts`，再转换
为 `test_case` Markdown。

本技能不再执行源码静态 spec 生成，也不把已有 spec 作为功能来源。详细规则见
[references/capture-workflow.md](references/capture-workflow.md)。

## 必须遵循的工作流

1. 扫描用户指定目录，识别前端子项目；存在多个候选时先让用户选择。
2. 读取项目 `playwright.config.*`、`package.json` 和 Vue Router 源码，按路由声明顺序
   访问静态路由；含 `:param` 或 `*` 的路由默认跳过，除非用户明确提供具体路由值。
3. 检查 `baseURL`、浏览器 channel、`executablePath`、登录状态和服务可用性。配置中
   的跨平台绝对浏览器路径无效时不得猜测，提示用户覆盖或修正。
4. 优先使用已有 `storageState`。用户明确提供账号密码时，可通过
   `--login-username` 与 `--login-password` 完成本次运行登录；凭据只在内存中使用，
   不写入任何输出文件。没有登录状态且用户未提供凭据时不得猜测。没有运行中的服务
   时，只有用户明确提供 `--start-command` 才启动服务，并且执行结束后只停止该进程。
5. 默认安全捕获：跳过删除、退出、保存、提交、导入、导出和其他高风险操作。用户
   明确要求时才使用 `--allow-destructive`。
6. 每个路由独立重置页面后捕获点击，避免前一个操作改变后续操作的页面状态。记录
   locator、点击名称、实际 URL 变化、Dialog 可见状态、失败原因和可选截图。
7. 每次输出到新的时间戳目录，保留历史版本；生成 `capture-report.json`，再使用
   技能内置 `spec2md` 转换当前版本的 `test_case` Markdown。
8. 只有浏览器真实观察到的 URL、Dialog 或点击结果才能写入 spec；未观察到的成功提示、
   API 结果、权限和业务结论不得补充。

## 命令

```bash
node "$SKILL_DIR/scripts/capture-playwright.js" \
  --project-dir <frontend-project> \
  --storage-state <storage-state-file> \
  --screenshots
```

用户明确提供账号密码时，可改用一次性登录参数；凭据不会写入输出：

```bash
node "$SKILL_DIR/scripts/capture-playwright.js" \
  --project-dir <frontend-project> \
  --login-username <账号> \
  --login-password <密码> \
  --screenshots
```

指定服务地址或启动命令：

```bash
node "$SKILL_DIR/scripts/capture-playwright.js" \
  --project-dir <frontend-project> \
  --base-url http://localhost:5173 \
  --start-command "npm run dev -- --host 0.0.0.0"
```

允许捕获高风险点击前必须明确授权：

```bash
node "$SKILL_DIR/scripts/capture-playwright.js" \
  --project-dir <frontend-project> \
  --allow-destructive
```

转换当前捕获版本：

```bash
"$SKILL_DIR/tools/spec2md/spec2md" \
  <capture-version-directory> \
  --renderer test_case \
  --merge-output \
  --out-dir <capture-version-directory>/test_case
```

## 输出

```text
<frontend>/tests/playwright-tester-create/YYYYMMDD-HHmmss/
├── 001-dashboard.spec.js
├── capture-report.json
├── route-002-initial.png       # 使用 --screenshots 时生成
└── test_case/merged.md
```

## 绝对边界

- 不凭源码或既有 spec 宣称浏览器执行成功。
- 不伪造凭据、测试数据、接口响应、成功提示或权限结果。
- 不自动安装依赖，不覆盖历史捕获目录。
- 不在未授权时点击破坏性控件。
- 不把捕获失败改写为测试通过。
