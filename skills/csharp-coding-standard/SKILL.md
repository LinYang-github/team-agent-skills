---
name: csharp-coding-standard
description: 面向 C#/.NET 项目的专项工程规范，覆盖语言与风格、项目结构、构建、资源所有权、内存与生命周期、类型与泛型、错误与异常、异步与并发、API 与版本、测试、工具链、可移植性和性能；通用日志、安全、提交与审查规则遵循 common-coding-standards。
---

# C# 编码标准

本技能用于新建、实现、重构和审查 C#/.NET 项目。目标是让所有权、生命周期、错误边界、异步关系、构建输入和程序集契约都能被代码、工具和测试验证。

## 使用边界

- 先加载并遵循 common-coding-standards；发生冲突时，以用户明确要求和通用技能的安全约束为准。
- 本技能只补充 C#/.NET 特有的语言、构建、资源、程序集和工具链决策，不重复日志级别、密钥、安全、Git 或代码审查等跨语言规则。
- 不将 C++、Go、前端/UI、特定业务系统、运维平台或某个项目的临时实现约定固化为通用标准。
- 默认优先使用本地工具、依赖和文档；除非用户明确授权，不引入在线资源。

## 默认工程基线

新项目没有更强约束时，采用：

- .NET 8 / C# 12；更低版本仅用于已确认的遗留工具链或必须面向 .NET Framework/.NET Standard 的库。
- .NET 9/C# 13 等更高版本特性仅在支持矩阵全部通过后启用，不作为默认。
- SDK 风格 .csproj；每个库、可执行程序和测试都是独立项目，依赖通过 PackageReference 传播。
- .editorconfig、Roslyn 分析器、编译器高等级警告、dotnet test 和 xUnit；配置文件随仓库提交。
- 自有代码警告视为错误；第三方和分析器规则通过单独配置或规则集隔离，不通过全局关闭警告迁就。
- 默认启用可空引用类型（NRT）；禁用 NRT 属于遗留兼容约束，需要显式记录并采用等价的可空性契约。
- 启用 <TreatWarningsAsErrors>、<EnableNETAnalyzers> 与 <AnalysisLevel>；公共 API 变更通过 PublicApi 测试守护。

已有项目优先识别现有基线并渐进迁移，不为追求形式一次性改写全部代码。

## 不可违背的原则

1. **资源必须有所有者。** 文件、句柄、连接、锁、定时器和注册关系由 IDisposable/IAsyncDisposable 类型管理，业务代码不裸写配对释放。
2. **引用不表示所有权。** 非拥有视图（Span、Memory、ref、IEnumerable）必须保证来源和有效期可理解；IDisposable 对象的所有者必须明确。
3. **生命周期必须可证明。** 不返回局部对象的 ref/span，不把对象释放后的访问和异步捕获留给调用者猜测。
4. **程序集必须自包含。** 每个项目独立可编译，公共 API 不依赖传递引用、全局可变状态或平台宽松行为。
5. **接口表达契约。** 可空性、所有权、单位、范围、失败方式和线程语义应由类型、名称或文档明确表达。
6. **错误不可跨边界失控。** 异常不得穿过进程、P/Invoke、COM、序列化和不兼容运行时边界；析构/finalizer 不得让异常逃逸。
7. **并发必须有边界。** Task、线程池、Channel 和等待时间有所有权、上限、取消和关闭路径；禁止无约束分离任务。
8. **API 与版本分开治理。** 公共类型、签名、可序列化结构和异常层次不得无约束暴露到稳定二进制/协议边界。
9. **平台差异集中隔离。** 路径、编码、P/Invoke、注册表和条件编译停留在适配层，不扩散到核心逻辑。
10. **工具检查不可绕过。** 不通过关闭警告、禁用分析器、删除测试或扩大忽略列表制造通过。
11. **优化需要证据。** 性能和内存优化先建立基线、目标与回归测试；不以“C# 更快”为由引入未验证复杂度。

## 标准工作流

1. 识别语言版本、.NET SDK、目标框架、构建系统、可空性策略和公共边界。
2. 检查项目、公共 API、所有权、错误、异步、协议、测试和发布产物，再选择相关参考文件。
3. 先确定接口契约和资源生命周期，再实现算法和基础设施；平台代码、第三方代码与核心逻辑保持边界。
4. 以最小兼容改动落地；公共 API、序列化结构或协议变化必须说明迁移影响。
5. 运行格式化、还原、编译、静态分析、测试和相应诊断；多目标框架项目至少验证受影响框架的构建配置。
6. 交付时报告语言/工具链假设、所有权与错误策略、验证结果、未覆盖平台和剩余风险。

## 主题路由

- 语言版本、命名、格式、编排和现代 C# 用法：阅读 [language-and-style.md](references/language-and-style.md)。
- 工程结构、MSBuild、项目与 NuGet：阅读 [project-structure-and-build.md](references/project-structure-and-build.md)。
- IDisposable、using、所有权和释放：阅读 [ownership-and-disposable.md](references/ownership-and-disposable.md) 与 [memory-and-gc.md](references/memory-and-gc.md)。
- 类、接口、泛型和委托：阅读 [types-and-generics.md](references/types-and-generics.md)。
- 异常、错误码和 Result 模式：阅读 [errors-and-exceptions.md](references/errors-and-exceptions.md)。
- async/await、Task、Channel 和同步：阅读 [async-and-concurrency.md](references/async-and-concurrency.md)。
- 公共 API、程序集版本和兼容：阅读 [api-and-versioning.md](references/api-and-versioning.md)。
- 测试、Roslyn 分析器和覆盖率：阅读 [testing-and-analysis.md](references/testing-and-analysis.md)。
- .NET SDK、跨平台、AOT 和发布工具链：阅读 [portability-and-toolchain.md](references/portability-and-toolchain.md)。
- 性能、GC、分配和确定性：仅在任务涉及这些约束时阅读 [performance-and-determinism.md](references/performance-and-determinism.md)。

## 输出契约

每次执行结束时至少说明：

- 处理模式：审查 / 设计 / 实现 / 回归。
- 工程基线：语言版本、.NET SDK、目标框架、构建系统与可空性策略。
- 核心决策：所有权、生命周期、错误、异步、API/版本和平台隔离。
- 修改影响：项目、公共 API、依赖、协议、序列化兼容和迁移要求。
- 验证结果：格式化、还原、编译、静态分析、测试和诊断的实际结果。
- 遗留风险：未覆盖平台、未验证边界、性能假设和已记录例外。
