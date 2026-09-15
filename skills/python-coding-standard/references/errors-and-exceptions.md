# 错误处理与异常

## 企业默认结论

- 普通应用和服务默认使用 Python 异常机制；禁用异常属于平台约束，需形成项目级决策记录。
- 预期内、调用者经常需要分支处理的失败，使用显式 `Result` 元组或 `Returns` 库；无法在当前层恢复的构造失败、资源失败和不变量破坏，可使用异常。
- 一个接口只采用一种主要失败通道，不同时混用返回码、`None`、全局错误和异常。
- 异常绝不跨越子进程、FFI/ctypes、RPC、消息队列和进程边界；边界处捕获、记录并转换。
- 清理完全依赖 `with`/上下文管理器，不使用成对手工清理路径维持异常安全。

## 错误模型选择

在模块或层级设计时先统一以下选择：

| 场景 | 默认方式 | 要求 |
| --- | --- | --- |
| 参数校验、未找到、冲突等预期失败 | `Result` 元组或错误码 | 调用者必须显式处理，错误类别稳定 |
| 构造、分配、文件打开等无法局部恢复的失败 | 异常 | 提供上下文，边界统一转换 |
| 可选数据不存在 | `Optional[T]`/`None` | 不携带失败原因时使用 |
| 程序不变量被破坏 | `assert`/`raise RuntimeError` | 不伪装成可恢复业务错误 |
| 子进程、FFI、RPC 或进程边界 | 稳定状态码和数据契约 | 不传播运行时异常对象 |

- 不使用 -1、0、空字符串或 `None` 同时表达多个错误含义。
- `Result` 元组必须保证“值”和“错误”互斥，并支持调用者无法忽略的检查方式。
- 错误码应稳定、可枚举、适合程序判断；面向人的消息用于诊断，不作为分支条件。
- 在保留原始错误类别的同时追加操作、资源标识和关键参数上下文，不重复记录同一错误链。

## 异常使用

- 异常表达异常失败，不用于正常循环、普通条件判断和协议分支。
- 抛出具体异常类型（`ValueError`、`TypeError`、`KeyError`、自定义异常），继承自 `Exception`。
- 每个模块或包都有自己的异常类，此异常类继承自 `Exception`。
- 重新抛出当前异常使用 `raise`（不带参数），避免 `raise exc` 重置堆栈。
- 捕获范围保持最小，只捕获能够恢复、补充上下文或转换的异常。
- 异常中不要使用裸露的 `except`，`except` 后跟具体的异常：

```python
# 好的写法
try:
    value = collection[key]
except KeyError:
    return key_not_found(key)
else:
    return handle_value(value)

# 不好的写法（try 范围过大）
try:
    # Too broad!
    return handle_value(collection[key])
except KeyError:
    # Will also catch KeyError raised by handle_value()
    return key_not_found(key)
```

- 禁止空 `except:`。确需忽略某类失败时，必须限定异常类型、说明原因，并保留必要的诊断或指标。
- `finally`/`__exit__`/`__del__` 不得抛出异常；清理失败通过显式 `close`、`commit`、日志或状态查询报告。
- 不直接抛出 `Exception`/`BaseException`/字符串或不具备稳定语义的内部类型。
- 自定义异常类继承 `Exception`，提供可读构造函数和 `__str__`，命名以 `Error`/`Exception` 结尾。
- 产生异常需要记录到日志中，对于需要用户确认的需要弹出提示信息。

## 异常过滤与上下文

- 使用 `except SpecificError as e` 绑定异常对象，提取上下文。
- `else` 子句用于 `try` 成功后的逻辑，避免误捕获 `else` 中的异常。
- `contextlib.suppress(SpecificError)` 用于显式忽略特定异常，限定类型并说明原因。
- 异常链（`raise NewError(...) from original`）保留原始上下文，不丢失根因。
- 不使用异常过滤掩盖设计缺陷；过滤条件应有明确业务或资源语义。

## 异步异常

- `async def` 方法的异常传播到返回的 `Task`/`Future`；调用者必须 `await` 才能观察。
- `asyncio.gather` 中多个任务失败时，默认第一个异常传播；`return_exceptions=True` 收集全部异常。
- 不使用 `asyncio.get_event_loop().run_until_complete(...)` 替代 `await`，避免阻塞事件循环。
- 异步入口设置必要的上下文，并建立异常屏障；任何异常都不能逃逸顶层任务。
- `asyncio.create_task` 创建的任务必须 `await` 或存储引用，否则异常可能被静默丢弃。
- 未处理的任务异常通过 `task.add_done_callback` 或 `loop.set_exception_handler` 捕获。

## 边界处理

- 每个线程入口、`asyncio` 任务顶层、`threading.Thread.run` 和回调必须有异常屏障，防止异常逃逸导致进程终止。
- `subprocess`/`ctypes`/`cffi` 调用捕获所有异常，转换为状态码/`HRESULT`，并将诊断写入受控错误对象。
- RPC、消息和序列化边界只传递稳定错误码、可安全展示的信息和关联标识，不传递 Python 类型名、栈对象或敏感路径。
- 第三方库错误在适配层转换为项目领域错误，不让调用方依赖第三方异常层次和数值错误码。
- 顶层兜底 `except Exception:` 仅用于隔离边界；它必须执行安全收敛、留下诊断并返回明确失败，不得让程序假装成功。

## 契约与断言

- `assert` 用于开发期发现程序员错误和内部不变量破坏，不用于处理不可信输入、网络数据和用户操作。
- 对外输入始终执行运行时校验（`if not isinstance(...): raise TypeError`），并返回定义良好的失败结果。
- 断言表达式不得包含改变程序状态的副作用；`python -O` 移除 `assert` 后行为必须保持一致。
- 不可恢复错误的终止策略、崩溃信息和敏感数据处理遵循通用规范与部署环境要求。

## 审查清单

- 调用者是否能从签名识别全部失败方式？
- 当前失败属于预期分支、异常失败还是不变量破坏？
- 异常是否可能越过线程、子进程、FFI 或进程边界？
- 失败后资源、对象状态和外部副作用是否一致？
- 错误上下文是否足够定位，同时避免重复记录和敏感信息泄露？
