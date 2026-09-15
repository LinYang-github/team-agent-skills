# 项目结构与构建

## 目录职责

按实际项目组织目录，不要求空目录齐全。新项目默认采用：

    pyproject.toml          构建与项目元数据事实来源
    README.md               项目说明与使用入口
    src/<package>/          源码（src 布局避免导入歧义）
    tests/                  单元与集成测试
    ruff.toml / pyproject    格式化与 lint 配置
    .python-version         pyenv/uv 指定解释器版本
    uv.lock / requirements  锁定的依赖版本

- 公共 API 与实现放在同一包；需要拆分时，公共契约包只放稳定接口。
- 入口点（`__main__.py` 或 `def main()`）只负责启动编排、配置、依赖装配和退出码，不承载业务算法。
- 不建立含义宽泛的 `common`、`utils`、`helpers` 模块；公共代码按明确职责归属子包。
- 构建产物（`__pycache__`、`.egg-info`、`dist`、`build`）、虚拟环境和临时数据不写入源码目录。

## pyproject.toml 基线

- 使用 `pyproject.toml` 作为构建与项目元数据事实来源；不使用 `setup.py` 作为主配置。
- 构建后端优先 `hatchling`/`setuptools`/`flit`；选择后保持一致，不为“先编过”随意切换。
- 依赖通过 `[project.dependencies]` 声明；开发依赖通过 `[project.optional-dependencies]` 或 `[dependency-groups]` 管理。
- `requires-python` 显式声明最低 Python 版本；不依赖解释器默认。
- 包发现配置（`[tool.setuptools.packages.find]`/`[tool.hatch.build]`）明确，不依赖隐式扫描。
- 项目元数据（名称、版本、作者、许可证、URL）完整且可追溯。
- 脚本入口通过 `[project.scripts]` 声明，不依赖手工安装 shell 脚本。

## src 布局与导入

- 优先 src 布局（`src/<package>/`）：测试从安装的包导入，避免误导入源码树根目录。
- 不使用 `sys.path` hack 修复导入；通过正确的包结构和可安装模式解决。
- 绝对导入优先，避免相对导入在重构后失效；包内部相对导入仅用于明确且稳定的子模块关系。
- 不使用 `import *`；确需导出公共 API 时使用 `__all__` 显式声明。
- 模块名小写下划线，包名小写无下划线；避免与标准库和常见第三方重名。

## 虚拟环境与依赖管理

- 每个项目使用独立虚拟环境（`venv`/`uv venv`/`poetry`），不污染系统解释器。
- 依赖版本通过锁文件（`uv.lock`/`poetry.lock`/`pip-tools` 生成带哈希的 `requirements.txt`）锁定，不在生产中拉取浮动版本。
- 包来源、版本、校验哈希和许可证可追溯；默认支持离线缓存或内部制品源。
- `pip install` 使用本地缓存或内部 PyPI 源；不在普通构建中从公网拉取浮动版本。
- 第三方源码记录来源、版本、补丁和许可证；修改第三方代码使用可重放补丁，不直接混入业务修改。
- 预览版包默认不引入生产；必须使用时锁定版本并记录理由和升级路径。
- 可选依赖通过 extras（`package[dev,test]`）声明，不在主依赖中混入开发工具。

## 配置与生成文件

- 编译期配置只包含平台能力、版本和确实影响类型的选项；运行时可变配置不写成常量或环境变量默认值。
- 配置文件使用 `pyproject.toml`、`config.toml`、`config.json` 或环境变量；敏感配置进入 `.env`（不入库）或受控密钥管理。
- 协议、IDL 和代码生成声明完整输入、输出和依赖；生成器版本受控，增量构建不会漏执行。
- 生成文件不手工修改；是否提交仓库由离线构建和发布需求决定，并保持来源可验证。
- 类型存根文件（`.pyi`）与实现同步；生成的 stub 不手工编辑。

## 打包与发布

- 包项目定义构建后端与元数据；公共 API、源码和资源分别成组。
- 发布产物包含版本、Python 版本要求、平台标签、依赖清单和许可证，不用文件名猜测兼容性。
- `python -m build`/`uv build` 后在干净虚拟环境运行消费者导入测试，避免只在源码树中可导入。
- 可执行程序的运行时依赖布局、入口点和配置位置由发布规则确定，不依赖用户修改全局环境。
- wheel 优先于 sdist 发布；platform wheel（含 C 扩展）按目标平台矩阵构建并验证。
- 命令行入口通过 `[project.scripts]` 声明，安装后可在 PATH 中调用。

## 构建验收

至少验证：

1. 从干净虚拟环境完成 `uv sync`/`pip install -e .`、`ruff check`、`mypy` 和 `pytest`。
2. 开发与生产依赖均可安装，不依赖本机全局状态。
3. 自有代码无 lint 与类型检查错误，依赖可从本地缓存或内部来源恢复。
4. `python -m build` 后消费者可以导入公共 API。
5. 修改公共选项、生成输入或依赖版本时能触发正确重建。
