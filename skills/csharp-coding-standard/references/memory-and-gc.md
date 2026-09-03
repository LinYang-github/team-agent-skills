# 内存与 GC

## 引用、Span 与视图

- `ref T` 表示必需且非空的借用；可空借用使用 `T?` 或 `IntPtr`/`Unsafe.AsPointer`。
- `Span<T>` 表示连续序列视图，`ReadOnlySpan<T>` 表示只读视图；二者不延长来源生命周期且不能装箱。
- `Memory<T>`/`ReadOnlyMemory<T>` 可作为字段、跨异步边界，但使用前必须证明来源有效。
- 不返回指向局部变量、临时对象、栈缓冲区或即将扩容集合的 `ref`/`Span`/`Memory`。
- 接收视图后需要异步保存或跨调用保留时立即复制到拥有类型（`T[]`、`ImmutableArray<T>`、`string`）。
- 不把临时 `Span` 隐式转换后的引用保存为成员，不从临时集合创建 `Memory`。

## 集合与迭代器失效

- 修改集合时确认枚举器失效规则；`List<T>` 扩容、`Remove`、排序后相关枚举器失效。
- 遍历过程中删除元素使用 `for` 循环配合索引或 `RemoveAll`，不依赖 `foreach` 内修改。
- 不把集合元素引用作为长期标识；需要稳定身份时使用领域 ID 或 `ImmutableArray<T>`。
- 并发读取集合时，只要任一线程可能修改就必须同步或使用 `ImmutableArray<T>`/`ConcurrentDictionary`。
- `IEnumerable<T>` 可能延迟执行；多次枚举重复执行源，必要时物化为 `ToList`/`ToArray`。

## 数组、缓冲区与字符串

- 优先 `T[]`、`Span<T>`、`ReadOnlySpan<T>` 和 `string`，不用裸指针传递长度不明的缓冲区。
- 边界接口同时携带数据和长度；不接受无法验证长度的 `IntPtr` 或 `byte*`。
- 使用 `.Length`、`.IsEmpty`，不通过哨兵值猜测集合状态；索引来自外部数据时先校验范围。
- 二进制数据使用 `byte`/`ReadOnlySpan<byte>`；不要依赖 `char` 的有符号性。
- 内存复制只用于 blittable 类型，并检查大小、重叠、对齐和字节序；对象序列化不得直接复制内存布局。
- 字符串默认 UTF-16；与 UTF-8 之间转换通过 `Encoding.UTF8`，不按字节截断字符序列。

## 异步与 lambda 生命周期

- 默认显式列出 lambda 捕获；异步、延迟或跨线程 lambda 禁止无条件捕获 `this`。
- 捕获 `this` 等同持有引用，不延长对象生命周期；必须证明任务结束早于对象 `Dispose`，或使用取消/`WeakReference`。
- `Task`、`ValueTask`、`CancellationTokenSource`、回调注册和 `Channel` 都可能延长生命周期，设计时画出拥有关系。
- 异步方法参数中的 `ref`/`Span`/`Memory` 必须在 `await` 期间保持有效；不把调用栈借用跨越 `await` 点（`ref struct` 不能跨越 `await`）。

## finalizer 与未定义行为防护

- 所有变量在使用前初始化；不读取 `out` 未赋值、未完成构造对象或已释放资源后的状态。
- 不违反类型安全；类型重解释优先 `Unsafe.As` 或字节视图，并满足尺寸与 blittable 要求。
- 不通过 `Unsafe` API 修改只读引用，不保留指向已释放 `SafeHandle` 的观察者。
- `unsafe` 代码集中隔离并审查；`fixed`/`GCHandle.Alloc` 必须成对释放，不依赖 GC 偶然回收。
- `Span<T>`/`ref struct` 不可装箱、不可作为字段、不可跨越 `await`；违反约束由编译器阻止。

## GC 与静态生命周期

- 避免可变静态对象和跨程序集静态初始化依赖；优先显式依赖注入。
- 静态可变字段需评估线程安全、重置和测试隔离；长生命周期缓存使用 `WeakReference` 或 `MemoryCache`。
- `AsyncLocal<T>`、`ThreadLocal<T>` 要评估线程池长期存活、上下文流动和异步边界。
- 单例不是生命周期设计的替代；必须说明初始化、并发、重置和测试隔离方式。
- 大对象（>= 85000 字节）进入大对象堆（LOH）；不假设 LOH 紧凑无碎片。

## pinned 与本机互操作

- pinned 对象使用 `fixed` 语句或 `GCHandleType.Pinned`，作用域最小化。
- 不长期 pin 对象；长期 pin 阻碍 GC 移动并增加碎片。
- 与本机代码互操作使用 `SafeHandle` 而非裸 `IntPtr`；所有权转移必须明确。
- 结构体布局使用 `[StructLayout]` 时记录对齐、`CharSet` 和 `Pack`，并验证跨平台一致性。

## 验证

- Debug/CI 使用 `DOTNET_GCLOG`、`GC.Collect` 测试和内存压力验证捕获泄漏。
- 并发共享内存使用静态分析和并发测试验证，不能仅靠 GC 正确性假设。
- 静态分析重点检查 `IDisposable` 未释放、可空引用、`Span` 生命周期和 `unsafe` 代码。
- 修复根因，不通过延长所有对象生命周期、全量 `SafeHandle` 或关闭检查掩盖错误。
