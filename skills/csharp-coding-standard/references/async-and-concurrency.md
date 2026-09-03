# 异步与并发

## 企业默认结论

- 异步设计必须明确任务所有者、数据所有者、取消方式、超时、背压和关闭顺序。
- .NET 项目优先使用 `async`/`await` 与 `CancellationToken` 管理可协作取消的异步操作；Task 对象不得无主存活。
- 禁止把 `async void` 作为规避 `async Task` 的手段（事件处理器除外）。`async void` 的异常无法被调用方观察。
- 优先使用不可变数据、消息传递、任务队列、`Channel<T>` 和所有权转移；共享可变状态是受控例外。
- 工作队列、线程池、缓存和生产消费通道必须有界，并定义满载策略。
- 原子操作默认使用 `Interlocked`；采用 `volatile`/`Interlocked.MemoryBarrier` 必须附并发协议、正确性说明和基准证据。

## async/await 基线

- 异步 I/O、网络、数据库和文件操作默认 `async`；不使用同步阻塞伪装异步。
- 异步方法返回 `Task`/`Task<T>`/`ValueTask`/`ValueTask<T>`；`ValueTask` 仅在热路径证明有收益时使用，并避免多次 await。
- 所有可取消的异步操作接受 `CancellationToken` 参数并传递到底层；不允许忽略取消。
- 异步方法命名以 `Async` 结尾（除非遵循框架约定，如 `DisposeAsync`）。
- 不使用 `.Result`/`.Wait()` 阻塞异步结果，避免死锁和线程池饥饿；入口可使用 `GetAwaiter().GetResult()` 仅在控制台 Main。
- 异步 lambda 谨慎捕获 `this`；必须证明任务完成早于对象 `Dispose`，或使用 `WeakReference`/取消。

## Task 与 ValueTask 生命周期

- 创建 `Task` 或提交异步操作的组件负责停止、等待和回收，不把生命周期责任隐式转交给调用者。
- 不直接散布 `new Thread`；通过 `Task.Run`、`ThreadPool`、`Channel` 或 `TaskScheduler` 集中管理。
- 线程入口设置必要的名称和上下文，并建立异常屏障；任何异常都不能逃逸 `Task`/`Thread`。
- 捕获到异步任务中的对象必须保证任务完成前有效；优先按值捕获不可变数据或转移所有权。
- `TaskCompletionSource<T>` 创建的 Task 必须有完成路径（成功/失败/取消），不依赖调用者遗忘完成。
- 禁止无保护地捕获 `this` 后让任务超越对象生命周期。使用受控所有权、`WeakReference` 检查、取消后等待，或把任务状态与对象分离。

## 有界执行与背压

- 线程池任务数量根据 CPU、阻塞特性和资源预算设定，不按请求、连接或数据项无限创建任务。
- `Channel<T>` 必须配置容量（`BoundedChannelOptions`），并明确 `FullMode`：等待、丢弃旧项、丢弃新项或写入失败。
- 提交接口返回可观察结果，不能静默丢任务。
- 生产者速度可能超过消费者时，在设计阶段建立背压；不得依赖内存耗尽或线程池饱和作为限流机制。
- 任务应具有合理粒度，避免过细调度成本或单个任务长期独占线程池。

## 锁与临界区

- 使用 `lock` 语句或 `Monitor`/`SemaphoreSlim`/`Mutex` 管理锁，禁止手工 `Enter`/`Exit` 分散在控制流中。
- 临界区只包含保护共享状态所需的最小操作；锁内不执行不受控 I/O、阻塞等待、外部回调或 `await`。
- 多把锁建立全局锁顺序；需要同时获取多把锁时优先一致顺序，避免死锁。
- 锁保护哪些数据必须在声明附近说明。共享状态和对应锁对象尽量封装在同一类型中。
- 不返回受锁保护对象的可变引用，使其在解锁后逃逸。
- `ReaderWriterLockSlim` 仅在读占绝对多数且基准证明有收益时使用；不要假定它必然更快或无饥饿。
- `SemaphoreSlim` 异步等待优先 `WaitAsync` 而非 `Wait`；混合同步/异步等待易死锁。
- `lock` 语句使用私有只读对象作为锁对象，不锁定 `this`、`typeof(T)` 或字符串。

## Monitor 与等待

- `Monitor.Wait`/`Pulse`/`PulseAll` 始终与谓词配合使用，并在循环中检查条件，以处理虚假唤醒。
- 修改受保护状态与检查谓词使用同一锁；通知时机应保证等待方能够观察新状态。
- 所有可能无限等待的操作必须评估超时、取消和关闭唤醒机制。
- 超时和持续时长使用 `Stopwatch`/`Environment.TickCount64`；表示日历时间时才使用 `DateTime`。
- 等待返回后必须区分条件满足、超时、取消和关闭，不把它们折叠为模糊的 `false`。

## 原子与无锁代码

- `Interlocked` 操作只保证相关原子变量的访问，不自动保护由多个字段组成的不变量。
- 优先使用锁表达复合状态；仅在性能数据证明锁是瓶颈且团队能够维护内存模型时采用无锁设计。
- 使用 `volatile` 或 `Interlocked.MemoryBarrier` 时，必须在代码附近写明同步关系、参与线程、发布对象和生命周期前提。
- `volatile` 不保证原子复合操作，只保证可见性；不用于发布对象初始化，使用 `Lazy<T>` 或 `Initializer`。
- 无锁算法必须测试 ABA、回收、溢出和伪共享，并通过专门审查。

## 数据发布与共享

- 对象在发布给其他线程前必须完成初始化，并通过锁、`Interlocked.Exchange`、`Channel` 或 `ImmutableArray<T>` 传递。
- 优先发布不可变快照；更新通过构造新值后原子替换或受锁交换完成。
- 不并发访问普通集合，即使不同线程看似操作不同元素，除非文档保证且集合结构不会变化。
- 缓存、单例和延迟初始化使用 `Lazy<T>` 或 `LazyInitializer.EnsureInitialized`，不手写双重检查锁定。
- `ConcurrentDictionary`、`ConcurrentQueue`、`ConcurrentBag` 用于并发场景，但仍需理解复合操作的原子性边界。
- 避免 false sharing；高频独立计数需要基准和布局检查后再使用对齐隔离。

## 取消与关闭

- 取消是协作协议。长循环、阻塞点和批处理边界定期检查 `CancellationToken`。
- `CancellationTokenSource` 负责 `Cancel`、`Dispose`，不把生命周期责任隐式转交。
- 关闭过程明确状态机：停止接收、请求取消、唤醒等待、排空或丢弃、等待完成、释放资源。
- `Close`/`Stop`/`Shutdown` 应尽可能幂等，并允许从预期控制线程安全调用。
- 不在持锁状态 `await` 可能反向获取该锁的操作；关闭顺序要消除循环等待。
- 超时退出后不得遗留仍访问已销毁状态的后台任务。

## 验证要求

- 并发单元测试覆盖启动、正常完成、取消、超时、队满、关闭竞争和异常路径。
- 使用 `SemaphoreSlim`、`CountdownEvent`、`Barrier` 或可控调度器协调测试，不用任意 `Task.Delay` 猜测调度时机。
- 使用 `DOTNET_THREADPOOL`、`ConcurrencyVisualizer` 或等价工具观察线程竞争。
- 对锁竞争、队列深度、任务延迟和拒绝量建立可观测指标，但不得输出敏感业务数据。
- 压力测试和长稳测试不能替代内存模型与生命周期审查。

## 审查清单

- 谁拥有 Task、线程和共享数据，何时结束？
- 队列和任务数是否有界，满载时会发生什么？
- 是否在持锁时 `await`、调用外部代码或执行 I/O？
- 是否存在对象先销毁、回调后到达或取消后仍运行的路径？
- 每个原子操作和无锁假设是否有明确证明与测试？
