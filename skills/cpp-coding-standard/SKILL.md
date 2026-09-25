---
name: cpp-coding-standard
description: 面向 C++ 项目的专项工程规范，覆盖语言与风格、构建、头文件、资源所有权、生命周期、类型与接口、错误、并发、API/ABI、存量 SDK 二次开发、测试、工具链、可移植性和性能；通用日志、安全、提交与审查规则遵循 common-coding-standards。
---

# C++ 编码标准

本技能用于新建、实现、重构和审查 C++ 项目。目标是让所有权、生命周期、错误边界、并发关系、构建输入和二进制契约都能被代码、工具和测试验证。

## 使用边界

- 先加载并遵循 common-coding-standards；发生冲突时，以用户明确要求和通用技能的安全约束为准。
- 本技能只补充 C++ 特有的语言、构建、资源、二进制和工具链决策，不重复日志级别、密钥、安全、Git 或代码审查等跨语言规则。
- 不将 Go、前端/UI、特定业务系统、运维平台或某个项目的临时实现约定固化为通用标准。
- 默认优先使用本地工具、依赖和文档；除非用户明确授权，不引入在线资源。

## 默认工程基线

新项目没有更强约束时，采用：

- C++20；更低标准仅用于已确认的遗留工具链，C++23 特性仅在支持矩阵全部通过后启用。
- target-based CMake；每个库、可执行文件和测试都是独立 target，依赖和编译要求通过 target 传播。
- clang-format、clang-tidy、编译器高等级警告、CTest 和 GoogleTest；配置文件随仓库提交。
- 自有代码警告视为错误；第三方头文件作为 system include 或隔离 target，不通过全局关闭警告迁就。
- 普通应用与服务默认启用异常；禁用异常、RTTI 或动态分配属于平台/实时约束，需要显式记录并采用统一替代契约。
- 内部及受支持编译器范围内发布的头文件默认使用 #pragma once；特殊 SDK/编译器兼容场景才使用宏式 include guard。
- Debug/CI 至少覆盖 AddressSanitizer 与 UndefinedBehaviorSanitizer；并发代码增加独立 ThreadSanitizer 作业。

已有项目优先识别现有基线并渐进迁移，不为追求形式一次性改写全部代码。

## 不可违背的原则

1. **资源必须有所有者。** 文件、内存、句柄、锁、线程和注册关系由 RAII 类型管理，业务代码不裸写配对释放。
2. **裸指针不表示所有权。** 独占默认值语义或 std::unique_ptr；共享所有权必须证明必要性，不能用 std::shared_ptr 掩盖生命周期设计。
3. **生命周期必须可证明。** 不返回悬空引用、迭代器、std::span 或 std::string_view，不把容器失效和异步捕获留给调用者猜测。
4. **头文件必须自包含。** 每个头文件独立包含即可编译，不依赖传递包含、预编译头或平台宽松行为。
5. **接口表达契约。** 可空性、所有权、单位、范围、失败方式和线程语义应由类型、名称或文档明确表达。
6. **错误不可跨边界失控。** 异常不得穿过 C ABI、插件、线程入口、进程或不兼容运行库边界；析构函数不得让异常逃逸。
7. **并发必须有边界。** 线程、队列、任务数和等待时间有所有权、上限、取消和关闭路径；禁止无约束分离线程。
8. **API 与 ABI 分开治理。** STL 类型、异常、编译器私有布局和平台类型不得无约束暴露到稳定二进制边界。
9. **平台差异集中隔离。** 路径、编码、动态库、系统类型和条件编译停留在适配层，不扩散到核心逻辑。
10. **工具检查不可绕过。** 不通过关闭警告、禁用 Sanitizer、删除测试或扩大忽略列表制造通过。
11. **优化需要证据。** 性能和内存优化先建立基线、目标与回归测试；不以“C++ 更快”为由引入未验证复杂度。
12. **SDK 兼容例外必须受控。** 通用规范是默认基线；经过验证并形成兼容性档案的 SDK 约束可以覆盖默认值，但覆盖范围只限 SDK 适配目标和边界代码，不得扩散到新业务代码。

## 标准工作流

涉及线程、任务、回调或异步资源时，先回答“异步任务四问”，再讨论实现细节：

1. **谁拥有**：线程、任务及其访问的数据由谁持有，能否超越对象生命周期。
2. **如何取消**：停止请求如何传递，长循环和阻塞点何时响应。
3. **如何等待**：正常完成、关闭和析构时由谁 join/等待，是否存在持锁等待或超时后仍访问已销毁状态。
4. **异常去哪**：线程或回调入口如何捕获全部异常、记录诊断并转换为可观察失败，禁止异常越过边界。

1. 识别语言标准、编译器/标准库、目标平台/架构、构建系统、异常/RTTI 策略、公开边界，以及是否受既有 SDK 的工具链、ABI、编码、所有权或线程模型约束。
2. 检查 target、头文件、所有权、错误、线程、协议、测试和发布产物，再选择相关参考文件。
3. 先确定接口契约和资源生命周期，再实现算法和基础设施；平台代码、第三方代码与核心逻辑保持边界。
4. 以最小兼容改动落地；公共 API、ABI、持久化或协议变化必须说明迁移影响。
5. 运行格式化、配置、编译、静态分析、测试和相应 Sanitizer；多平台项目至少验证受影响平台的构建配置。
6. 交付时报告语言/工具链假设、所有权与错误策略、验证结果、未覆盖平台和剩余风险。

## 主题路由

- 语言版本、命名、格式和现代 C++ 用法：阅读 [language-and-style.md](references/language-and-style.md)。
- 头文件、自包含、包含顺序与防重复包含：阅读 [headers-and-includes.md](references/headers-and-includes.md)。
- 工程结构、CMake、target 与依赖：阅读 [project-structure-and-build.md](references/project-structure-and-build.md)。
- RAII、所有权、内存和生命周期：阅读 [ownership-and-raii.md](references/ownership-and-raii.md) 与 [memory-and-lifetime.md](references/memory-and-lifetime.md)。
- 类、接口、模板和泛型：阅读 [classes-interfaces-and-templates.md](references/classes-interfaces-and-templates.md)。
- 异常、错误码和 noexcept：阅读 [errors-and-exceptions.md](references/errors-and-exceptions.md)。
- 并发、锁和原子操作：阅读 [concurrency-and-synchronization.md](references/concurrency-and-synchronization.md)。
- API、ABI 和版本兼容：阅读 [api-and-abi-compatibility.md](references/api-and-abi-compatibility.md)。
- 测试、静态分析和 Sanitizer：阅读 [testing-and-sanitizers.md](references/testing-and-sanitizers.md)。
- 编译器、跨平台和发布工具链：阅读 [portability-and-toolchain.md](references/portability-and-toolchain.md)。
- 基于存量或专有 SDK 的二次开发、插件开发与兼容性治理：阅读 [sdk-based-development.md](references/sdk-based-development.md)。
- 性能、分配、实时性和确定性：仅在任务涉及这些约束时阅读 [performance-and-determinism.md](references/performance-and-determinism.md)。

## 输出契约

每次执行结束时至少说明：

- 处理模式：审查 / 设计 / 实现 / 回归。
- 工程基线：语言标准、编译器/标准库、平台/架构、CMake 与异常/RTTI 策略。
- SDK 约束：如适用，报告 SDK 版本、兼容组合、编码契约、资源与线程边界以及采用的例外。
- 核心决策：所有权、生命周期、错误、并发、API/ABI 和平台隔离。
- 修改影响：target、公共头文件、依赖、协议、二进制兼容和迁移要求。
- 验证结果：格式化、配置、编译、静态分析、测试和 Sanitizer 的实际结果。
- 遗留风险：未覆盖平台、未验证边界、性能假设和已记录例外。
