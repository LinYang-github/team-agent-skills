# 业务场景契约

业务场景契约是前端源码中的静态测试设计数据，用来表达页面级业务流程。它不替代页面源码，也不读取既有 spec；生成器会用页面源码、service、i18n 和契约共同生成 spec。

默认扫描：

```text
<project>/src/test-contracts/**/*.scenario.json
<project>/src/test-contracts/**/*.scenario.js
<project>/src/test-contracts/**/*.scenario.ts
```

契约文件必须是静态对象，不能调用函数、读取运行时状态或执行任意代码。推荐使用 JSON，或者使用 `export default { ... }` 的对象字面量。

## 最小结构

```js
export default {
  route: '/users',
  scenarios: [
    {
      id: 'search-users',
      title: '用户管理 - 查询用户',
      preconditions: [
        { action: 'navigate', route: '/users' }
      ],
      steps: [
        {
          action: 'fill',
          target: { placeholder: '搜索用户' },
          value: 'alice'
        },
        {
          action: 'click',
          target: { role: 'button', name: '查询' },
          waitFor: { method: 'GET', path: '/api/users', status: 'ok' }
        }
      ],
      effects: [
        { assertion: 'row-exists', target: { role: 'row' } }
      ]
    }
  ]
}
```

## 支持的操作

`navigate`、`click`、`fill`、`select`、`check`、`uncheck`、`press`。

定位目标支持：

```js
{ testId: 'user-submit' }
{ css: '.shortcut-btn' }
{ role: 'button', name: '查询' }
{ role: 'button', nameKey: 'common.query' }
{ placeholder: '搜索用户' }
{ label: '用户名' }
{ text: '创建成功' }
```

`nameKey`、`labelKey`、`placeholderKey` 和 `textKey` 会从项目中文 i18n 源码解析。无法解析时不得猜测。

## 值和接口等待

普通字符串、数字和布尔值会原样生成。敏感值只能引用环境变量：

```js
{ env: 'TEST_PASSWORD' }
```

唯一用户名可以使用：

```js
{ generator: 'uniqueUsername', prefix: 'test_' }
```

接口等待必须明确写出方法和路径：

```js
{
  method: 'POST',
  path: '/api/users',
  status: 'ok',
  query: { appCode: 'auth' }
}
```

## 支持的断言

`visible`、`hidden`、`text`、`url`、`value`、`checked`、`row-exists`、`row-disappears`。

契约没有写出的成功提示、数据变化、权限结论和接口结果不得由生成器补充。

## 失败处理

契约解析或渲染失败时：

- 不生成包含猜测内容的步骤；
- 将文件、场景和错误写入 `manifest.json` 的 `unresolved`；
- 没有关联有效契约的路由仍可使用源码功能点模式生成。
