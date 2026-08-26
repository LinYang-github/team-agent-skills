# Go 并发与生命周期

- 每个 goroutine 都要有启动者、职责、退出条件、取消信号和错误归属；禁止“放后台就不管”。
- 优先通过 context、channel 或明确的同步原语表达协作；共享可变状态必须有锁、原子操作或单线程所有权。
- channel 的创建者负责关闭；接收方不要关闭不拥有的 channel；关闭、取消和重复关闭行为要有测试。
- 使用 sync.WaitGroup、errgroup 或等价机制等待任务结束，并传播第一个错误或完整错误集合。
- ticker、timer、worker、HTTP server 和后台清理任务在停止时显式 Stop/Close，避免泄漏。
- 涉及共享状态、取消和关闭时运行 go test -race；不要以加锁掩盖未定义的所有权。
