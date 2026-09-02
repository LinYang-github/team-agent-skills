# 语言版本与代码风格

## 语言基线

- 新项目默认 .NET 8 / C# 12，通过 `<LangVersion>` 显式声明，不依赖 SDK 默认值。
- 遗留项目使用更低版本时记录受限特性、目标工具链和迁移条件；不能因个别旧模块把所有项目降级。
- C# 13 及以上特性只有在 .NET SDK、分析器、运行时、调试器和目标平台矩阵全部支持后启用。
- 禁止依赖实验性或预览特性而不加隔离；必须使用时限制在适配层，并对其他目标框架提供实现或明确失败。

## 格式化

- 仓库提交统一的 .editorconfig，格式化结果由工具决定，不在代码审查中反复争论个人排版。
- 公司规范要求代码块内统一缩进一个 Tab 长度；建议使用 4 空格，且 .editorconfig 与 csharpier/dotnet format 保持一致。
- 行宽默认不超过 120；公司规范要求每行代码和注释不超过 70 个字符或屏幕宽度，超过则换行，换行后缩进一个 Tab。
- 大括号、属性对齐、命名空间样式和 using 排序统一由配置控制。
- 格式化只作用于本次修改范围；大规模机械格式化使用独立提交，避免掩盖语义变更。

## C# 命名默认

| 元素 | 默认形式 | 示例 |
| --- | --- | --- |
| 类、接口、枚举、委托、记录 | PascalCase | AppDomain |
| 枚举值 | PascalCase | FatalError |
| 事件、属性、方法 | PascalCase | ValueChanged / ToString |
| 命名空间 | PascalCase | System.Drawing |
| 字段 | camelCase | myField |
| 局部变量、参数 | camelCase | typeName |
| 常量与静态只读字段 | PascalCase | MaxRetryCount |
| 接口 | I 前缀 + PascalCase | IDisposable |
| 异常类 | Exception 后缀 | WebException |
| 私有字段（可选下划线） | _camelCase | _buffer |

- 同一代码库已有一致且成熟的命名约定时优先渐进保持，不在功能修改中全量重命名。
- 不使用匈牙利命名法，不把类型编码进变量名；单位或语义差异应进入名称或强类型。
- 布尔值使用可判断真假的名称，如 `IsReady`、`HasValue`、`CanRetry`；避免否定叠加。
- 缩写按普通单词处理，保持跨项目一致；领域缩写只有在团队词汇表中明确时使用。
- 不应使用缩写或首字母缩写词，如用 `OnButtonClick` 而不用 `OnBtnClick`。
- 资源（菜单按钮、按钮、文本框、表格、统计图）标示符使用 camelCase，尽量简洁但不牺牲可读性。

## 代码编排

- 空行规则：
  - 类、接口之间留两行空行。
  - 方法之间留一行空行。
  - 局部变量与其后语句之间留一行空行。
  - 方法内功能逻辑部分之间留空行。
- 函数长度：每个函数有效代码（不含注释和空行）不超过 50 行。
- 花括号：公司规范要求开括号 `{` 放在块所有者的下一行、单起一行；闭括号 `}` 单独放在代码块最后一行、单起一行。若团队 .editorconfig 统一为 K&R 风格，则以配置为准，不在审查中反复争论。
- 空格规则：
  - 括号与其内字符之间不加空格；括号与其前关键词之间留空格，如 `while (true)`。
  - 方法名与左括号之间不加空格。
  - 参数之间逗号后加一空格，如 `Method1(int i1, int i2)`。
  - `for` 语句表达式之间加空格，如 `for (expr1; expr2; expr3)`。
  - 二元操作符与操作数之间用空格隔开，如 `i + c`。
  - 强制类型转换时类型与变量之间加空格，如 `(int) i`。

## 注释与文档

- 通用注释原则遵循 common-coding-standards。
- 类、字段、属性、构造函数、方法、事件均需注释（自动生成的类除外），采用 XML 注释：`<summary>` 节概要说明，`<param>` 节描述参数（Sender 和 e 参数无需注释），`<returns>` 描述返回值，`<exception>` 描述抛出的异常。
- 方法内单行注释尽量用 `//` 简要说明，避免用 `/* */` 做较长解释。
- 单行注释以 `//` 开始，`//` 与文本之间插入一个空格，单行注释不要放在代码末尾。
- 公共接口说明所有权、可空性、异常/错误、线程安全、单位和生命周期，不重复函数名。
- 非直观的泛型约束、内存序、序列化布局和平台差异必须说明“为什么”；临时兼容代码记录移除条件。
- 不保留注释掉的代码、IDE 自动生成说明或已经失真的实现叙述。

## 文档编排

建立的类/窗体中的字段、属性等按如下顺序添加：

```csharp
/// <summary>
/// 开发者：张三
/// 开发时间：2022-3-31 14:44:51
/// 版本：V1.0.0
/// 描述：当前类描述
/// </summary>
class MyClass
{
    #region 类型
    #endregion

    #region 字段
    #endregion

    #region 属性
    #endregion

    #region 构造函数
    #endregion

    #region 方法
    #endregion

    #region 事件
    #endregion
}
```

## 初始化与类型

- 对象在声明处完成初始化；优先对象初始化器与 `required` 成员，避免可空未初始化警告。
- 使用 `var` 消除重复类型或承接 LINQ、匿名类型结果；当类型影响单位、符号、所有权或精度时显式书写。
- 协议、文件和二进制接口使用固定宽度整数；容器大小和索引使用领域类型或经检查转换后的类型。
- 禁止未检查的窄化、符号混用和浮点转整数；集中使用受检查的算术或在关键路径显式 `checked`。
- 使用 `enum`，需要标志位使用 `[Flags]`；序列化值与枚举显式映射，不依赖数值顺序。
- 使用 `null`、可空引用类型与 `Nullable<T>` 表达可空性，不使用哨兵值。
- 使用 `record` 和 `record struct` 表达值语义数据；使用 `init` setter 保护不变量。
- 使用 `const` 表达真正编译期常量；运行时常量使用 `static readonly`。

## 函数与控制流

- 函数保持单一职责；参数过多或多个布尔开关时使用选项对象或参数对象，不用位置参数猜测语义。
- 优先早返回降低嵌套；复杂条件提取为命名局部函数或方法。
- 默认按值返回结构体或按引用返回大对象；不返回指向局部对象的 ref/span。
- 输入参数按值、`in`、`ref`、`out` 或 `ReadOnlySpan<T>` 选择，所有权和生命周期必须清楚。
- 输出优先使用返回值；多个结果使用具名元组或命名结构体，不使用无语义大量输出参数。
- 不使用 `ref`/`out` 参数切换多个行为；优先拆分函数或返回结果对象。
- 避免在重载中随意给参数命名，重载成员参数名应保持一致：

```csharp
// 好的写法
public int IndexOf(string value) { ... }
public int IndexOf(string value, int startIndex) { ... }

// 不好的写法
public int IndexOf(string value) { ... }
public int IndexOf(string str, int startIndex) { ... }
```

- 避免使重载成员的参数顺序不一致：

```csharp
public EventLog();
public EventLog(string logName);
public EventLog(string logName, string machineName);
public EventLog(string logName, string machineName, string source);
```

## 自动验收

- CI 运行 `dotnet format --verify-no-changes` 或 csharpier 检查格式。
- .editorconfig 与分析器配置在 CI 中校验，不依赖开发者手工记忆格式规范。
- 公共 API 变更通过 PublicApi.Shipped/Unshipped 文件和测试守护。
