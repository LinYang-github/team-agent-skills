# 插件组包 Skill

[plugin-packager](../skills/plugin-packager/SKILL.md) 将产品项目已有的 Skill、MCP、MCP Apps、可选 Agent 和业务工作台入口 整理为 HuiMate 可导入的插件目录与 ZIP。使用 Python 3.10+，脚本仅依赖标准库，不启动产品服务、不联网、不发布制品。

## 来源与维护

完整技能迁自 [HuiMate](https://github.com/WuFuxiu/HuiMate)，迁移源提交为 `30515e6dc90d91f4cf54c03a16d6770fdf889a92`，原目录为 `skills/plugin-packager/`。脚本和交付参考原样迁移；入口描述按团队校验器要求调整措辞，使用范围不变。本仓库是后续修改的唯一入口，不接受由原项目自动覆盖同步；维护版本见 [manifest.yaml](../manifest.yaml)。

团队成员从 `develop` 创建工作分支并提交 PR。修改支持范围或格式时同步技能内的[交付契约](../skills/plugin-packager/references/delivery-contract.md)和回归。产品项目可以复制完整技能目录；不要只复制 `SKILL.md`。组包时不放入各产品 Skill 根目录下的 `evals/`（评估提示与预期答案），因为安装后的模型能读取插件中的全部文件。

## 业务工作台

产品同时提供业务工作台和 MCP/Skill 时，在同一插件根目录生成可选 `.workbenches.json`，无需第二次上传领域文件。声明只包含入口名称、解析方式与 URL 边界，不打入业务数据库或运行时。普通管理页面与 MCP Apps 分开，详细格式见[工作台交付契约](../skills/plugin-packager/references/workbenches.md)。

## 验证

```bash
./scripts/validate-skills.sh
./scripts/run-python.sh -m unittest discover -s tests -p 'test_*.py'
```

独立回归将技能复制到临时目录，以 Python 隔离模式执行，检查附件与摘要、普通 MCP 与 MCP Apps、必填配置、错误引用、凭据文件及输出覆盖保护。这些测试由仓库既有 pre-push 门禁执行。

HuiMate 的平台兼容性回归使用其 `skills.lock.json` 锁定本仓库提交和文件摘要，再交给平台实际 ZIP 解析器与发现器检查。锁定版本只证明已测版本与该平台基线的兼容性；技能升级后需要在消费项目更新锁并复测。上述检查不代表真实模型、外部服务或页面验收。
