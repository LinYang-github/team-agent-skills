# 性能、实时性与确定性

本文件只在任务具有明确性能、时延、内存或确定性约束时使用。通用“先测量再优化”原则遵循 common-coding-standards。

## 性能契约

- 优化前记录工作负载、数据规模、硬件、运行模式（Release/AOT）、指标基线和目标；不能用 Debug 构建结果推断 Release 性能。
- 区分吞吐、平均时延、尾时延、启动时间、峰值内存、GC 暂停、分配次数和二进制体积，不以单一“更快”替代目标。
- 基准测试固定输入、预热、采样和统计方式，使用 BenchmarkDotNet 避免测量陷阱；结果进入可重复的性能回归流程。
- 性能变化同时检查正确性、资源上限和最坏路径，不用平均值掩盖长尾。
- GC 暂停时间纳入时延目标；server GC 与 workstation GC 的选择由部署模式决定。

## 数据与分配

- 优先改善算法复杂度、数据布局和不必要拷贝，再考虑微观语法优化。
- 热路径避免无界分配、隐式字符串构造、LINQ 多次枚举和重复集合扩容；已知规模时使用 `Capacity`/`ArrayPool<T>`。
- 默认值语义；只有测量证明拷贝成本显著且生命周期清楚时引入 `Span<T>`、`ref` 或对象池。
- 结构体布局、缓存局部性、false sharing 和对齐优化需要基准和平台验证，不手工 padding 猜测。
- `ArrayPool<T>`、`ObjectPool<T>` 和 `MemoryPool<T>` 只用于已证明的分配瓶颈，并定义上限、回收、线程安全和故障行为。
- `stackalloc` 用于小尺寸栈上缓冲；大尺寸回退到 `ArrayPool` 或堆分配，避免栈溢出。

## Span 与低分配

- `Span<T>`/`ReadOnlySpan<T>` 用于零拷贝切片和视图；不延长来源生命周期，不装箱。
- `Memory<T>` 用于跨异步边线的低分配视图；`MemoryHandle` pin 后及时释放。
- `string` 创建使用 `string.Create`/`Span<char>` 减少中间分配；避免重复 `string.Concat`/`+` 拼接。
- `InterpolatedStringHandler` 自定义用于性能关键日志，避免无谓格式化。
- `Utf8Parser`/`Utf8Formatter` 替代 `Encoding.UTF8.GetString` 用于二进制边界。

## GC 与延迟模式

- GC 模式（server/workstation/background）由部署目标决定；高吞吐服务默认 server GC，低延迟交互默认 workstation/background GC。
- 避免大对象堆（LOH）碎片；>= 85000 字节的对象进入 LOH，不假设紧凑。
- 长生命周期对象用于缓存；短生命周期对象分配在 Gen0 快速回收，避免提升到 Gen2。
- `GC.AllocateUninitializedArray`/`GC.Pause` 等高级 API 仅在已证明的瓶颈中使用，并记录理由。
- `fixed`/`GCHandle` pin 最小化；长期 pin 阻碍 GC 移动并增加碎片。
- 实时路径不依赖 GC 暂停保证；硬实时场景评估 NativeAOT 或禁用 GC 的特殊配置。

## 实时与确定性

- “实时”必须明确是软实时还是硬实时，并给出周期、截止时间、抖动、丢帧/降级和超限行为。
- 实时路径禁止未界定的动态分配、阻塞 I/O、无界锁等待、反射加载和不可控日志格式化。
- 资源在初始化阶段预分配并验证容量；容量耗尽时采用已定义的失败或降级路径，不静默扩容破坏时限。
- 使用 `Stopwatch`/`Environment.TickCount64` 测量间隔；`DateTime.Now` 受系统时钟和时区影响，不用于间隔测量。
- 调度优先级、CPU 亲和性和平台实时 API 属于平台适配层，不能散落到算法代码。
- NativeAOT 用于启动时间和内存占用敏感场景；评估反射、动态加载和序列化兼容性。

## 数值与可复现

- 对结果可复现有要求时，明确浮点模型、舍入、并行归约顺序、随机种子、编译优化和硬件差异。
- 不假设不同 .NET 运行时和硬件加速路径产生逐位相同浮点结果；需要逐位一致时必须设计专门算法和测试。
- 随机算法显式传入 `Random`/`Random.Shared`，不在核心计算中隐式使用全局随机状态。
- `checked`/`unchecked` 算术显式表达溢出策略；关键数值路径默认 `checked`，热路径证明安全后局部 `unchecked`。
- `BigInteger` 仅用于真正的大数；普通整数路径不引入 `BigInteger` 性能开销。

## 反射与动态

- 反射（`Type.GetType`、`MethodInfo.Invoke`）用于框架和设计时，不用于热路径业务逻辑。
- 源生成器（`IIncrementalGenerator`）替代运行时反射实现序列化、注册和 DI，减少启动时间和 AOT 兼容性。
- `Expression<TDelegate>` 编译用于动态查询，但编译成本高，结果应缓存。
- `DynamicMethod`/`ILGenerator` 仅在已证明的反射瓶颈中使用，并记录替代方案。
- NativeAOT/Trimming 发布前验证反射调用点；`DynamicDependency` 标注最小化。

## 性能代码审查

- 复杂优化代码必须说明基线、收益、适用规模和退化条件。
- 关键基准进入 CI 或定期性能流水线（BenchmarkDotNet + ReportGenerator），并设置能容忍环境噪声的回归阈值。
- 删除已经失去收益的缓存、池化、手写 SIMD 和平台分支，不让历史优化永久增加复杂度。
- 对象池、`ArrayPool` 和缓存必须配置上限、回收和线程安全策略，避免成为内存泄漏源。
