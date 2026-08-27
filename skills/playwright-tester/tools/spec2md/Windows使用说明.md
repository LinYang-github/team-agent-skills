# spec2md 使用说明

> Playwright Spec → code2doc Markdown 转换工具

## 文件说明

```
spec2md/
├── spec2md.exe              # 主程序，直接双击运行
├── run.bat                  # 快捷启动脚本
├── Windows使用说明.md       # 本文件
├── template_*.json          # 模板文件
├── examples/                # 示例文件目录
├── output/                  # 输出目录（运行后生成）
└── vscode-extension/        # VS Code 扩展
    ├── spec2md-*.vsix       # VS Code 安装包
    └── VS_CODE_INSTALL.md   # 安装说明
```

## 快速开始

1. 双击 `run.bat` 或直接运行 `spec2md.exe`
2. 在文件浏览器中右键 `.spec.ts` 文件，选择 `spec2md:转换为测试用例MD`
3. 查看 `output` 目录中的 `.md` 文件

## 命令行使用

```cmd
# 查看帮助
spec2md.exe --help

# 转换单个 spec 文件为测试用例
spec2md.exe tests/example.spec.ts

# 转换为用户手册
spec2md.exe --renderer user_manual tests/example.spec.ts

# 指定输出目录
spec2md.exe --out-dir ./docs tests/

# 指定输出文件
spec2md.exe -o custom_output.md tests/example.spec.ts

# 集成 Playwright 测试报告
spec2md.exe --report playwright-report.json tests/example.spec.ts
```

## 输出模式

| 渲染器 | 输出类型 | 用途 |
|--------|----------|------|
| test_case | 测试用例设计表 | code2doc 测试用例设计 |
| case_log | 测试用例执行记录 | code2doc 测试执行记录 |
| user_manual | 用户手册操作步骤 | 用户操作手册 |

## 常见问题

**Q1: 窗口闪退，什么都没发生**
- 检查 spec 文件是否存在
- 使用 cmd 命令行运行查看错误信息

**Q2: 中文拼音标注异常**
- 确保系统已安装中文字体

**Q3: 找不到模板文件**
- 模板文件已内置在 exe 中，无需单独配置

## 注意事项

1. 建议在安全的内网环境使用
2. 配置文件可选，不影响基本功能
3. 支持 glob 通配符：`spec2md.exe tests/**/*.spec.ts`

## VS Code 扩展

如需在 VS Code 中使用，请查看 `vscode-extension/VS_CODE_INSTALL.md`。
