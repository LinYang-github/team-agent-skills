# 所有权与 IDisposable

## 默认所有权模型

- 首选值语义：对象由作用域、集合或成员直接拥有，GC 负责回收。
- 持有非托管资源或必须显式释放的资源时，类型实现 `IDisposable`（同步）或 `IAsyncDisposable`（异步）。
- 需要独占可释放所有权时，由拥有者负责 `Dispose`/`DisposeAsync` 调用，不裸写配对释放。
- 多个独立所有者确实需要共同延长同一对象生命周期时，提供共享所有权包装（如引用计数句柄），但需证明必要性。
- `WeakReference`/`WeakReference<T>` 只用于观察对象，不把 `TryGetTarget` 失败当作不可能。
- 非拥有视图（`Span<T>`、`Memory<T>`、`ref`、`IEnumerable<T>`）都不延长来源生命周期；接口必须保证来源和有效期可理解。
- 不在业务代码中直接调用 `Marshal.AllocHGlobal`/`FreeHGlobal`、`GCHandle.Alloc`/`Free` 或平台句柄配对函数，必须由 `SafeHandle` 等包装类型管理。

## IDisposable 覆盖范围

以下资源必须由不可复制的释放类型或 `SafeHandle` 管理：

- 文件、目录、流、socket、管道句柄。
- 数据库连接、事务、命令。
- 互斥锁、信号量、`SemaphoreSlim`、`ManualResetEvent`、`CancellationTokenSource`。
- 定时器、`Timer`、`PeriodicTimer`、任务调度注册。
- COM 对象、GCHandle、非托管内存、映射内存和平台句柄。
- 临时文件、事务、状态切换以及必须成对恢复的设置。

释放包装器在构造或工厂中建立有效状态，在 `Dispose` 中无异常释放；释放操作需要报告失败时提供显式 `Close`/`Commit`，并让 `Dispose` 执行安全兜底。

## using 规则

- 使用 `using` 声明（`using var x = ...;`）或 `using` 语句管理可释放对象，禁止手工 `Dispose` 分散在控制流中。
- 同一作用域多个 `using` 声明按逆序释放；复杂控制流优先显式 `using` 语句块以明确释放时机。
- 持有 `IDisposable` 成员的类必须实现 `IDisposable`（必要时 `IAsyncDisposable`）并在 `Dispose` 中释放成员。
- `using` 声明不得用于跨越异步边界的资源；异步释放使用 `await using`。
- 不为“避免拷贝”把普通值改成可释放包装；先确认资源类型、生命周期和释放成本。

## 复制与移动

- 类是引用类型，赋值是引用共享；可释放类必须明确所有权转移或禁止复制。
- `record` 默认值语义但仍是引用类型；持有可释放成员的 record 需自定义释放策略。
- `struct` 是值类型，按值复制；可释放 struct 会因复制导致重复释放，应使用类或 `SafeHandle`。
- `ref struct`（如 `Span<T>`）不可装箱、不可作为字段，用于栈上临时视图。
- 不依赖 finalizer 替代显式释放；finalizer 只作为未托管资源的安全网，且必须正确实现 dispose 模式。

## Dispose 模式

- 实现 `IDisposable` 时遵循标准 dispose 模式：`Dispose()`、可选 `Dispose(bool disposing)`、可选 finalizer。
- `Dispose(bool disposing)` 中只释放非托管资源时允许 `disposing == false`；托管资源仅在 `disposing == true` 时释放。
- 调用 `Dispose` 后对象应处于可安全调用但无效的状态；重复调用 `Dispose` 必须幂等。
- 实现可释放的类型应标记 `GC.SuppressFinalize(this)`，避免 finalizer 重复回收。
- 释放操作不得抛出异常；失败通过显式 `Close`、`Commit`、日志或状态查询报告。

## 工厂与构造失败

- 构造完成后对象应满足类不变量；不能产生“构造成功但必须再 init”的半成品。
- 可能失败且无法用异常表达的创建过程使用命名工厂并返回项目统一 `Result<T>` 类型或 `OneOf<T, Error>`。
- 工厂返回值或 `IDisposable`；不通过输出裸句柄转移所有权。
- 多步资源获取依赖局部 `using` 对象，任一步失败都自动回滚已获取资源。

## 回调与注册

- 注册接口返回 `IDisposable` 订阅令牌，`Dispose` 时解除注册；不要求调用者记忆配对 `Unregister`。
- 异步回调不得无条件捕获 `this`；根据执行器与对象生命周期选择值捕获、`WeakReference` 或显式取消。
- 对象 `Dispose` 前停止新回调、取消任务并等待正在执行的回调退出，避免回调访问已销毁成员。
- 事件订阅（`+=`）必须有对应 `Dispose` 中的 `-=`；长生命周期对象订阅短生命周期对象是内存泄漏重点。

## 审查问题

1. 每个资源由谁创建、拥有、释放，异常路径是否一致？
2. 接口中的引用和视图是否明确非拥有、可空和有效期？
3. 共享所有权是否确实必要，而不是修补设计？
4. `Dispose`、取消、关闭能否并发发生，结果是否定义？
5. 资源释放是否发生在创建它的模块或运行时边界内？
