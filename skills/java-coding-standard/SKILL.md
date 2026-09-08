---
name: java-coding-standard
description: Use when implementing, refactoring, reviewing, testing, or designing Java projects, including Java APIs, concurrency, exceptions, logging, security, MySQL, Maven or Gradle builds, Spring applications, and JVM delivery concerns. For a matching task, read this SKILL.md before answering; when the user asks for a rule source, use its routed reference file rather than inventing one.
---

# Java 开发规范

本技能用于编写、重构、审查、测试和设计 Java 项目。它是独立的 Java 专项规范，不依赖其他 Skill，也不默认引入 JDK 8、Maven、Spring Boot、MySQL 或任何特定技术栈。

## 使用边界

- 先以目标项目的事实为准：读取 `pom.xml`、`build.gradle*`、工具链配置、现有代码、测试和 CI，识别 JDK、构建工具、框架、ORM、数据库及项目约定。
- 不能确认的基线只在它会改变实现时询问；不为了补全清单而阻塞任务。
- 只使用目标 JDK 可用的语法和 API；沿用项目现有 Maven、Gradle 或其他构建入口。
- Spring、ORM、MySQL 和测试框架只在项目已使用或用户明确选择时适用。
- Velocity、iBATIS、旧 JDK API、固定服务器参数等历史或特定环境条款，仅在对应技术存在时直接适用；否则只作背景参考。
- 对存量项目渐进修正，不为形式一次性改写无关代码，不自动安装依赖或替换技术栈。

## 规则优先级

发生冲突时按以下顺序处理：

1. 安全、法律合规、数据完整性和平台硬约束。
2. 用户当前明确要求。
3. 项目已有且可验证的规范与技术栈。
4. Java 参考规范的【强制】、【推荐】、【参考】。

不得弱化第 1 级。其他冲突必须说明差异、选择和影响，不静默覆盖项目约定。

## 参考路由

只读取当前任务命中的文件；多主题任务可组合读取，但禁止默认一次加载全部规范。

- 命名、常量、格式、OOP、集合、并发、注释、日期时间和通用 Java 编码：读取 [01-coding-standards.md](references/01-coding-standards.md)。
- 异常语义、错误边界、日志级别、参数和脱敏：读取 [02-exception-logging.md](references/02-exception-logging.md)。
- 单元测试、可测试性、用例边界和回归要求：读取 [03-unit-testing.md](references/03-unit-testing.md)。
- 输入校验、访问控制、敏感数据和应用安全：读取 [04-security-standards.md](references/04-security-standards.md)。
- MySQL 建表、索引、SQL、MyBatis/ORM 映射与参数绑定、事务和性能：读取 [05-mysql-database.md](references/05-mysql-database.md)。
- 任务出现 MyBatis、SQL XML、`#{}` 或 `${}` 时，必须以 `references/05-mysql-database.md` 为规范依据；即使问题表现为 SQL 注入，也不改引为安全规范。
- 应用分层、目录、依赖、服务器和工程结构：读取 [06-project-structure.md](references/06-project-structure.md)。
- 架构、接口、设计原则、扩展性和模式：读取 [07-design-standards.md](references/07-design-standards.md)。
- 术语、版本说明、参考资料和条款背景：仅在需要溯源或解释时读取 [08-appendix.md](references/08-appendix.md)。

## 工作流

1. 确认任务模式：设计、实现、重构、审查或回归。
2. 识别实际技术基线、受影响边界和项目已有风格。
3. 按路由读取最少的参考章节，将条款区分为当前必须、建议和不适用。
4. 在真实公开契约、数据流、并发与异常边界上实施最小改动；保留项目现有的正确惯例。
5. 使用项目现有入口运行相关格式化、编译、静态检查和测试；不将未执行的检查宣称为通过。
6. 交付时说明采用的技术基线、规范依据、修改影响、验证结果和未覆盖风险。

## 执行要点

- 编写代码时，优先满足正确性、安全性和资源边界，再处理命名与格式；不为一次需求增加抽象层。
- 审查代码时，只报告有代码证据且可操作的问题，指出条款级别、影响和最小修正；项目事实不足时不猜测。
- 设计 API 时明确可空性、输入范围、异常、并发、事务和兼容契约；集合返回空集合还是 `null` 以现有公开契约为准，新接口默认避免返回 `null`。
- SQL 使用参数化，不将外部输入拼接进语句。
- 涉及时间、集合、并发和字符串时，考虑时区、线程安全、空值、可变性和比较语义，不只追求示例可编译。

## 输出契约

根据任务需要，结果应包含：

- 处理模式与已识别的 JDK、构建工具、框架和存储基线。
- 主要技术决策及其规范依据；有冲突或例外时说明取舍。
- 对公开 API、依赖、数据、并发、兼容性和迁移的影响。
- 实际执行的编译、测试、静态检查及结果；未执行项和原因。
- 遗留风险、未验证边界和已记录例外。
- 用户要求规范溯源时，先读取对应参考文件，再引用本 Skill 中实际存在的 `references/<文件名>.md` 路径和条款等级；不得编造路径或条款。

参考规范完整保留了《阿里巴巴 Java 开发手册（黄山版）》的条款、分级和正反例；本入口只负责适用性判断与按需路由。
