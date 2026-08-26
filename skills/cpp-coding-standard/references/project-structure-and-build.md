# 项目结构与构建

## 目录职责

按实际 target 组织目录，不要求空目录齐全。新项目默认采用：

    CMakeLists.txt
    CMakePresets.json
    cmake/                 项目 CMake 模块
    include/<project>/     对外公共头文件
    src/                   库的私有实现
    apps/                  可执行程序入口
    tests/                 单元与组件测试
    tools/                 开发或数据工具
    third_party/           必须随仓库交付的受控第三方代码

- 公共头文件只放稳定接口；私有头文件靠近实现，不因“以后可能复用”提前暴露。
- main 函数只负责启动编排、配置、依赖装配和退出码，不承载业务算法。
- 不建立含义宽泛的 common、utils、helpers 目录；公共代码按明确职责归属 target。
- 构建产物、下载缓存、生成文件和临时数据不写入源码目录。

## CMake 基线

- 使用 target-based CMake，不使用目录级全局 include、link 或 compile definitions 管理普通依赖。
- 每个库、可执行文件、插件和测试是独立 target；target 名称在项目内稳定且可搜索。
- 使用 target_sources、target_include_directories、target_link_libraries、target_compile_features 和 target_compile_definitions。
- PUBLIC、PRIVATE、INTERFACE 按真实传播关系选择；不能为了“先编过”全部写 PUBLIC。
- 禁止使用全局 include_directories、link_directories 和 add_definitions 污染无关 target。
- C++ 标准通过 target_compile_features 声明；禁用编译器扩展，除非目标平台明确依赖。
- 项目 CMake 模块只封装重复且稳定的构建语义，不把普通 target 定义隐藏在不可追踪的宏中。

## target 类型

- 业务库优先真实 STATIC/SHARED target；是否共享由部署和 ABI 策略决定，不依赖 BUILD_SHARED_LIBS 偶然切换公共产品形态。
- 纯头文件库使用 INTERFACE target，并在测试中至少实例化主要接口。
- 第三方库通过 imported/alias target 接入，不向业务 target 暴露裸库路径和全局变量。
- Object library 只用于确实需要复用相同对象文件的场景，不替代清晰的库边界。
- 可执行程序链接业务库，不复制编译同一批源码。

## Preset 与构建类型

- 仓库提交 CMakePresets.json，至少覆盖开发 Debug、发布 Release 和 CI 验证配置。
- 单配置与多配置生成器均可工作；不得假设 CMAKE_BUILD_TYPE 在所有生成器中存在。
- 本地私有路径、凭据和机器专用 SDK 位置进入 CMakeUserPresets.json 或受控环境配置，不提交仓库。
- 输出目录和安装布局由 CMake 统一管理，不依赖 IDE 默认路径或手工复制。

## 依赖管理

- 依赖名称、来源、版本、校验值/锁文件、许可证和目标平台可追踪；默认支持离线缓存或内部制品源。
- 优先使用组织既有且可锁定的包管理方案；CMake 代码面向标准 imported target，不把包管理器细节扩散到业务目录。
- FetchContent 默认不在普通构建中从公网拉取浮动版本；必须使用时锁定不可变版本并提供离线来源。
- third_party 中的源码记录来源、版本、补丁和许可证；修改第三方代码使用可重放补丁，不直接混入业务修改。
- 第三方警告与自有代码分离，不能通过全局关闭警告降低自有代码质量。

## 配置与生成文件

- 编译期配置只包含平台能力、版本和确实影响类型/布局的选项；运行时可变配置不写成预处理宏。
- 配置头使用 configure_file 等确定性步骤生成到构建目录，并通过 target include 路径暴露。
- 协议、IDL 和资源生成声明完整输入、输出和依赖；生成器版本受控，增量构建不会漏执行。
- 生成文件不手工修改；是否提交仓库由离线构建和发布需求决定，并保持来源可验证。

## 安装与发布

- 库 target 定义 install/export 规则；公共头文件、运行时、调试符号和开发文件分别成组。
- 发布产物包含版本、架构、编译器/运行库、构建类型和依赖清单，不用文件名猜测兼容性。
- install 后在干净目录运行消费者构建或冒烟测试，避免只在源码树中可链接。
- 可执行程序的运行时依赖布局、动态库搜索路径和配置位置由安装/打包规则确定，不依赖用户修改全局环境。

## 构建验收

至少验证：

1. 从干净构建目录完成 configure、build 和 test。
2. Debug 与 Release 均可配置，受支持生成器不依赖本机 IDE 状态。
3. 自有 target 无编译警告，依赖可从本地缓存或内部来源恢复。
4. install/export 后消费者可以找到公共头文件和 target。
5. 修改公共选项、生成输入或依赖版本时能触发正确重建。
