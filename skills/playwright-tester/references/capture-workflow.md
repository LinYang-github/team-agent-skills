# 浏览器捕获规则

## 配置和服务

捕获器读取：

- `package.json`：确认 Playwright 依赖；
- `playwright.config.ts/js/mjs/cjs`：读取 `baseURL`、`channel` 和浏览器路径；
- Vue Router：获取静态路由和路由顺序。

没有 `baseURL` 时必须由用户传入 `--base-url`。已有 `storageState` 时优先使用；
用户明确提供账号密码时，可用 `--login-username` 与 `--login-password` 完成本次登录，
凭据只在内存中使用，不写入任何输出文件。没有 `webServer` 或运行中服务时，只有用户
明确传入 `--start-command` 才可以启动服务。不得停止用户原本启动的服务。

## 捕获对象

默认捕获实际可见且未禁用的：

- `button`
- `a[href]`
- `[role="button"]`
- `[role="link"]`
- `input[type="button"]`
- `input[type="submit"]`

定位优先级：

```text
data-testid → role + accessible name → id → class + index
```

每个点击操作都会从该路由重新开始，避免状态污染。

## 风险控制

以下名称默认跳过：删除、移除、撤销、清空、退出、新建、创建、保存、确定、提交、
导入、导出及对应英文词。用户必须显式传入 `--allow-destructive` 才能捕获这些操作。

除用户明确提供的登录账号密码外，捕获器不会填写业务表单或猜测账号密码，也不会确认
真实业务数据是否正确；它只记录实际点击后的 URL 变化和 Dialog 是否可见。

## 运行时证据

`capture-report.json` 记录：

- 路由顺序和动态路由跳过项；
- 每个路由的初始 URL；
- 每个点击的定位信息；
- 点击后的实际 URL；
- Dialog 是否可见；
- 点击或导航错误；
- 安全模式和配置警告。

只有这些运行时证据可以进入生成的 spec。没有观察到的接口响应、成功提示、列表变化
和权限结果必须保留为空，不得推断。
