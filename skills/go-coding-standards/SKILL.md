---
name: go-coding-standards
description: 统一 Go 项目的工程实现方式，补充 Go 的包结构、错误处理、应用生命周期、配置启动、有界并发、协议、文件与 API 契约、测试和构建实践；通用编码原则遵循 common-coding-standards。
---

# Go 编码规范

## 目标

在 common-coding-standards 的通用底线之上，统一 Go 项目的包边界、错误语义、并发控制、资源释放、测试和构建习惯。优先使用标准库和项目已有依赖，避免为了局部便利引入不可维护的抽象。

## 适用范围

当用户要求以下事项时启用本技能：

- 新增或重构 Go 服务、命令行程序、Worker、库和后台任务。
- 设计 Go 包结构、模块依赖、接口、错误、并发和资源生命周期。
- 设计 Go 应用的启动、运行、优雅退出、配置校验和依赖组装。
- 处理有界并发、任务队列、背压、长连接和协议兼容性。
- 设计流式文件处理、路径安全、API 错误契约和可测试的基础设施边界。
- 处理 gofmt、go vet、静态检查、单元测试、竞态检测和构建发布。

先读取并遵循 common-coding-standards；本技能只补充 Go 特有的实现方式，不重复通用命名、提交、脱敏和交付规范。

## 不可违背的原则

1. **小接口和清晰包边界。** 包按职责组织，避免循环依赖、万能包和通过 internal/外部路径绕过边界。
2. **错误带上下文。** 使用显式 error 返回；在跨层传递时保留根因和操作上下文，调用方按 errors.Is/errors.As 或等价语义判断，不用字符串比较错误类型。
3. **并发有所有权。** 每个 goroutine 都能说明启动者、退出条件、取消方式和资源释放责任；不启动没有停止路径的后台 goroutine。
4. **上下文可取消。** 外部请求、数据库、网络、子进程和长任务优先传递 context，并设置合理的超时和取消路径。
5. **资源成对释放。** 文件、连接、响应体、锁、临时目录、Ticker 和子进程都覆盖正常与异常退出路径；可使用 defer 的地方保持释放靠近获取。
6. **标准工具优先。** 代码格式、测试和基础诊断优先使用 Go 官方工具链；新增第三方库要说明必要性、版本和维护影响。
7. **应用生命周期可控。** 初始化、运行、停止和资源关闭有明确顺序；后台任务都能取消、等待和报告失败，优雅退出不能只关闭监听端口。
8. **并发和数据规模有边界。** goroutine、队列、连接、消息、请求体和缓存都有容量、超时或取消限制；过载时有背压、拒绝或降级策略。
9. **跨边界契约稳定。** API、协议、文件和存储适配器使用显式输入输出、机器可读错误和兼容策略，不把内部实现或原始错误暴露给调用方。

## 标准工作流

1. 读取 go.mod、go.sum、目录结构、入口、配置、日志、测试和构建脚本。
2. 先判断包职责、依赖方向、错误边界和 goroutine/资源所有权。
3. 按需读取 references 中的 Go 专项规范，并同时遵循 common-coding-standards。
4. 实施最小改动，避免为局部问题重写包结构或替换核心依赖。
5. 至少运行 gofmt、go vet、相关 go test；涉及并发时运行竞态检测，涉及构建时验证目标平台产物。
6. 交付时说明公开包/API、配置、依赖和迁移影响。

## 参考资料路由

- 包结构、模块、接口和依赖方向：阅读 references/packages-and-modules.md。
- error、context、HTTP/数据库调用和资源释放：阅读 references/errors-context-and-resources.md。
- goroutine、channel、锁、取消和竞态：阅读 references/concurrency-and-lifecycle.md。
- 应用启动、依赖组装、信号处理和优雅退出：阅读 references/application-lifecycle.md。
- 配置来源、启动校验和运行时配置边界：阅读 references/configuration-and-bootstrap.md。
- 有界并发、任务队列、背压和关闭语义：阅读 references/bounded-concurrency-and-backpressure.md。
- HTTP/长连接超时、心跳、关闭和消息限制：阅读 references/network-and-long-connection.md。
- 协议 envelope、请求关联、版本兼容和幂等：阅读 references/protocol-and-compatibility.md。
- 流式 IO、文件安全、原子写入和存储适配器：阅读 references/storage-and-files.md。
- API 错误分类、错误响应和内部诊断边界：阅读 references/api-errors-and-contracts.md。
- gofmt、vet、测试、竞态检测和构建：阅读 references/testing-and-tooling.md。

## 输出契约

除 common-coding-standards 的输出契约外，说明：

- Go 版本、模块和目标平台。
- 包/接口边界以及错误和 context 传播方式。
- 应用生命周期、配置校验、goroutine、资源释放、容量边界和构建/测试策略。
- 实际运行的 Go 工具命令和结果。

## 禁止事项

- 不用 panic 代替可处理的业务错误，不在库代码中随意 panic。
- 不启动没有取消、退出或错误上报路径的 goroutine。
- 不把 context 存进长期持有的结构体或作为可选参数滥用。
- 不为通过检查而跳过 gofmt、vet、测试或竞态检测。
