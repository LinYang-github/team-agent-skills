# CLI 设计

## 定位

CLI 是领域包面向人、脚本、CI 和 Agent 设施的稳定产品接口，不是调试脚本集合。它可以同时承载领域业务调用和设施运维，但必须通过命名空间分开，并映射到同一能力 ID、应用服务和 API 契约。

## 主命令命名

### 默认建议

- 同时包含业务调用、运行管理和客户端集成时，使用 `<product>ctl`，例如 `acmectl`。
- 主要是终端中的用户工作流、几乎不含运维动作时，可以直接使用简短产品名，例如 `acme`。
- 一个领域包默认只有一个稳定主命令；MCP、迁移器或后台服务作为子命令或内部入口，不再要求用户记忆多个可执行文件。
- 命令使用小写 ASCII，短、可读、可搜索，避免空格、下划线、组织缩写堆叠和容易冲突的通用词。
- Python、npm、Homebrew 等发行包名可以与命令名不同，但主命令一旦公开应保持稳定，并在领域包清单中声明映射。

### 不推荐

- `domain-cli`、`tool`、`server`、`manager` 等缺少领域识别度的名字。
- 把实现语言写入命令名，例如 `acme-python`。
- 把传输实现作为主要产品入口，例如要求用户分别使用 `acme-mcp-server` 和 `acme-api-server`。
- 仅因品牌调整立即删除旧命令；应保留兼容别名、弃用提示和明确移除版本。

Windows 可以生成同名 `.exe`，文档和脚本仍引用不带扩展名的稳定命令。

## 推荐命令树

以下是能力目录，不是强制套餐。只实现产品真实具备的部分：

- 仅远程 API 的领域包：通常需要 `version`、`capability`、领域资源命令、`config/profile` 和连接诊断。
- 带项目级本地实例：再增加 `workspace`、`runtime` 和日志诊断。
- 向 Agent 或编辑器提供能力：再增加 `integration` 和 `mcp serve`。
- 提供团队共享服务：按需增加 `auth login/logout/whoami`，认证实现必须符合组织安全规范。

```text
<product>ctl
├── version
├── package
│   ├── describe
│   ├── validate
│   └── check
├── capability
│   ├── list
│   └── describe <capability-id>
├── <resource>
│   ├── list | search | get
│   ├── create | validate
│   ├── preview | apply
│   └── publish | open
├── workspace                 # 存在项目级工作区时
│   ├── init
│   ├── status
│   └── path
├── runtime                   # 存在本地受管进程时
│   ├── start | stop | restart
│   ├── status | logs
│   └── doctor
├── config
│   ├── list | get | set | unset
│   └── path | explain
├── integration               # 向外部客户端投影贡献时
│   ├── list
│   ├── install
│   ├── status
│   └── uninstall
├── mcp serve                 # 提供 MCP 时
├── auth login|logout|whoami  # 提供需登录的共享服务时
└── completion                # 需要终端补全时
```

小型 CLI 可以把高频的 `start`、`stop`、`status`、`doctor` 放在根级。命令增长后应收敛到 `runtime` 命名空间，并为旧入口保留兼容期。

### 三种“安装”必须分开

- 安装程序本身：交给系统包管理器，例如 Python tool、npm、Homebrew 或企业软件分发。
- 初始化业务项目：`workspace init`，只创建当前 scope 的配置和数据目录。
- 安装 Agent/编辑器贡献：`integration install --client <client> --scope <scope>`。

根级 `install` 容易混淆程序、工作区和客户端配置，不作为默认设计。

程序自身升级同样优先交给原包管理器。只有已经建立签名、渠道、回滚和离线策略时，才提供自更新命令；不要让普通业务 `update` 同时承担程序升级和资源修改两种语义。

## 领域业务命令

- 使用稳定资源名作为一级命名空间，动作作为子命令；资源名采用小写 `kebab-case` 并在所有文档中保持单复数一致。
- `list/search/get` 必须只读；不得因读取或页面打开隐式保存。
- `create` 明确创建资源；`validate` 和 `calculate` 返回判定或计算结果而不写正式数据。
- 高风险或正式基线变更使用 `preview` → `apply`，并携带 `preview-id`、`expected-version` 和稳定幂等键。
- `publish` 与普通 `apply` 分开，明确不可变快照、审批和审计语义。
- 避免一个模糊的 `update` 整块覆盖聚合；优先使用字段级 patch、明确领域动作或经服务端管理的变更集。
- 输入复杂时支持 `--file <path>` 或标准输入，不把大段 JSON 塞进命令参数；提供 `--schema` 或文档链接说明输入契约。

## 全局参数

只为真实能力提供参数，并在所有子命令保持同义：

| 参数 | 用途 |
| --- | --- |
| `--project-root <path>` | 显式指定项目根；省略时按定义好的规则发现 |
| `--server <url>` | 本次调用显式覆盖服务地址 |
| `--profile <name>` | 选择命名配置，不与 scope 混用 |
| `--scope project\|user` | 安装、配置或工作区操作的作用域 |
| `--output table\|json\|yaml` | 人读或机器可读输出 |
| `--quiet` / `--verbose` | 控制诊断详细度，不改变数据语义 |
| `--no-color` | 禁用 ANSI，CI 或重定向时默认生效 |
| `--timeout <duration>` | 设置有界调用超时 |
| `--expected-version <value>` | 乐观并发控制 |
| `--idempotency-key <value>` | 可重试写入的幂等标识 |
| `--dry-run` | 展示计划且保证不产生副作用 |
| `--yes` | 跳过允许自动确认的提示，不绕过禁止自动化的审批 |

配置优先级默认采用：命令行显式参数 → 环境变量 → 项目配置 → 用户配置 → 安全默认值，并通过 `config path` 或 `config explain` 说明最终来源。密码、Token 等秘密不要放在命令参数、普通配置文件或日志中，优先使用密钥存储、受保护环境注入或标准输入。

## 输出契约

- 成功数据写入 `stdout`，诊断、警告和进度写入 `stderr`。
- `--output json` 时成功输出必须是单个有效 JSON 文档，不混入日志、颜色或进度动画；字段变更遵循兼容策略并包含必要的 schema/version 信息。
- 非交互环境不等待提示。缺少确认时返回明确非零退出码，并说明可用的 `--dry-run`、`--yes` 或确认参数。
- TTY 表格用于人读；列宽裁剪不得影响 JSON/YAML 输出中的完整值。
- 资源写入成功后输出稳定资源 ID、当前修订、实际服务端结果和可执行的回读命令。
- 调用失败不得输出成功措辞；部分成功必须显式列出成功项、失败项和是否可安全重试。

## 退出码与错误

退出码是公开契约，应在文档中稳定声明。可以采用下列建议映射，也可以遵循组织既有标准：

| 退出码 | 建议语义 |
| --- | --- |
| `0` | 成功 |
| `2` | 命令用法或参数错误 |
| `3` | 配置、工作区或依赖错误 |
| `4` | 资源不存在 |
| `5` | 版本冲突或并发冲突 |
| `6` | 服务或网络不可达 |
| `7` | 未认证或无权限 |
| `8` | 业务校验失败 |
| `9` | 部分成功 |

机器输出模式下，错误至少包含稳定错误码、简短消息、可操作建议和关联 ID；不得用本地化显示文本代替可编程错误码。堆栈只在明确的调试模式输出。

## 自动化与交互安全

- 所有读取命令和 `--help`、`version`、`status`、`doctor` 不产生业务写入。
- `--dry-run` 必须由测试证明无副作用，不能只是改变提示文字。
- 交互确认只在 TTY 出现；CI 中必须显式提供确认或失败退出。
- 重试仅用于已知幂等操作，并具有次数和时间上限；不无限重试写入。
- 删除数据、覆盖用户配置、发布正式版本等动作使用专用显式参数，不能由宽泛的 `--yes` 意外授权。
- CLI 通过同语言 SDK/API client 或应用服务执行能力；不得解析 Web 页面、直接修改数据库或复制一套只在命令行存在的业务规则。

## 兼容与测试

至少验证：

- 所有命令的 `--help`、必填参数、非法组合和退出码；
- JSON 输出可被程序解析，重定向时无 ANSI 和诊断污染；
- 配置优先级、scope、含空格路径及环境变量覆盖；
- 只读命令无写入，`--dry-run` 无副作用；
- 幂等安装/卸载、重复 start/stop、失效 runtime 和端口冲突；
- `expected-version` 冲突不覆盖数据，幂等键重试只应用一次；
- 旧命令别名给出弃用提示并保持约定兼容期；
- 清单中的能力、CLI 命令、API/MCP 映射和安装态资产一致。
