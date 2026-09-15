# 能力与契约

## 能力是稳定的产品语义

领域包清单应以能力为中心，而不是以当前路由、按钮或函数为中心。公共能力必须有稳定标识；若组织没有既定规范，可采用 `<domain>.<resource>.<operation>`。

对每项公共能力至少声明：

- 稳定 `capabilityId`；
- 资源类型和稳定 ID 字段；
- 操作语义；
- read-only、destructive、idempotent 等风险属性；
- 所需权限与确认策略；
- public、compatibility 或 internal 稳定级别；
- Skill、CLI、MCP、API、Web、event 等贡献渠道；
- 契约版本和弃用策略。

同一能力可以有多个渠道，但渠道不得改变业务语义。MCP tool、CLI command 和页面操作应能追溯到同一个能力 ID 和应用服务。

## 契约分层

```text
领域语义和不变量
        ↓
应用服务 / Use Case
        ↓
版本化 API 与事件契约
        ↓
SDK、CLI、MCP、Web 适配器
```

- API 定义跨进程请求、响应、错误、版本和鉴权边界。
- SDK 是 API 的客户端封装，可以生成，也可以手写；它不是第二套服务端业务层。
- CLI 面向人和脚本，将命令参数转换为公共能力调用。
- MCP 面向 Agent，将工具和资源映射为公共能力调用。
- Web 面向人机交互，通过 SDK 或同一 API 调用应用服务。
- 算法库位于服务端领域实现内部，不能直接访问外部系统数据库。

## 最小清单轮廓

具体 schema 可以按组织标准调整，但应覆盖以下语义：

```yaml
metadata:
  packageId: example.domain
  domainId: example
  version: 1.0.0
ownership:
  domainAggregates: [example-resource]
  hostOwned: [work-item, conversation, cross-domain-relations]
resources:
  - id: example-resource
    stableIdField: resourceId
capabilities:
  - id: example.resource.read
    resource: example-resource
    operation: read
    stability: public
    risk:
      readOnly: true
      destructive: false
      idempotent: true
      confirmation: none
    channels: [skill, cli, mcp, api, view]
contributions:
  skills: []
  cli: []
  api: []
  mcp: []
  views: []
  events: []
runtime:
  modes: [按实际部署声明]
```

清单是发现和一致性检查的事实来源，不应包含机器绝对路径、临时端口、源码工作区假设或真实业务数据。

## 写入协议

高风险、不可逆或会改变正式业务基线的写入优先采用：读取当前状态 → 生成预览 → 用户确认 → 携带预览标识、期望版本和幂等键应用 → 回读验证。普通低风险编辑可以采用更轻的交互，但仍要保留并发控制、错误语义和可追溯性。版本冲突不得静默覆盖。

观察与编辑必须分离：打开页面、切换选项、关闭抽屉、刷新或组件卸载不得隐式改变领域修订。编辑态在本地标记 dirty，取消恢复最近已保存基线，显式保存或确认应用才可调用写入能力。服务端应提供字段级或领域动作级更新，避免一个页面使用过期快照整块覆盖聚合。

## Canonical 表示与旧值兼容

- 每个公共字段只定义一个 canonical 枚举或结构，服务端、Web、SDK、CLI 和 MCP 对外生成相同表示。
- 兼容层可在边界读取旧别名并立即规范化，但新写入、计算分派和返回值不得继续生成旧表示。
- 旧值与 canonical 值必须走同一业务分支；不得因为前端未识别旧值而默认到另一算法或规则。
- 测试至少覆盖旧值读取、canonical 新写入、跨渠道语义一致和兼容层未被绕过。

## 一致性验证

- 存在 SDK 时，从 API 契约生成或校验 SDK，阻止 schema 漂移。
- 比较清单、API operation、MCP tool、CLI command 和页面能力映射。
- 验证 public 能力在源码态和安装态具有相同语义。
- 删除或修改公共能力时执行兼容性检查，并提供弃用窗口。
