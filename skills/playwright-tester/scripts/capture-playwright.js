#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { spawn } = require('node:child_process');

const SOURCE_EXTENSIONS = new Set(['.js', '.jsx', '.ts', '.tsx', '.vue']);
const IGNORED_DIRS = new Set(['.git', 'node_modules', 'dist', 'build', 'coverage', 'playwright-tester-create', 'test-results']);
const RISKY_WORDS = /删除|移除|撤销|清空|退出|注销|登出|新建|创建|保存|确定|提交|导入|导出|delete|remove|revoke|logout|sign.?out|create|save|submit|import|export/i;

function fail(message) {
  console.error(message);
  process.exit(1);
}

function readText(file) {
  try {
    return fs.readFileSync(file, 'utf8');
  } catch {
    return '';
  }
}

function parseArgs(argv) {
  const args = {
    projectDir: null,
    baseUrl: null,
    routes: [],
    storageState: null,
    loginUsername: null,
    loginPassword: null,
    startCommand: null,
    headed: false,
    allowDestructive: false,
    maxActions: 40,
    waitMs: 500,
    screenshots: false,
    outputDir: null,
    browser: null,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === '--project-dir') args.projectDir = argv[++index];
    else if (value === '--base-url') args.baseUrl = argv[++index];
    else if (value === '--route') args.routes.push(argv[++index]);
    else if (value === '--storage-state') args.storageState = argv[++index];
    else if (value === '--login-username') args.loginUsername = argv[++index];
    else if (value === '--login-password') args.loginPassword = argv[++index];
    else if (value === '--start-command') args.startCommand = argv[++index];
    else if (value === '--headed') args.headed = true;
    else if (value === '--allow-destructive') args.allowDestructive = true;
    else if (value === '--max-actions') args.maxActions = Number(argv[++index]);
    else if (value === '--wait-ms') args.waitMs = Number(argv[++index]);
    else if (value === '--screenshots') args.screenshots = true;
    else if (value === '--output-dir') args.outputDir = argv[++index];
    else if (value === '--browser') args.browser = argv[++index];
    else if (value === '--help' || value === '-h') args.help = true;
    else fail(`未知参数: ${value}`);
  }
  return args;
}

function printHelp() {
  console.log(`用法:
  node scripts/capture-playwright.js --project-dir <前端工程> [选项]

说明:
  按源码发现的静态路由访问真实页面，记录可安全点击的控件并生成版本化 spec。

选项:
  --base-url <URL>          覆盖 Playwright 配置中的 baseURL
  --route <路径>            只捕获指定路由，可重复；默认按源码路由顺序
  --storage-state <文件>    使用已有登录状态
  --login-username <账号>    使用用户明确提供的账号登录，本次运行不保存凭据
  --login-password <密码>    使用用户明确提供的密码登录，本次运行不保存凭据
  --start-command <命令>    启动本次服务，结束后只停止该进程
  --headed                  使用有头浏览器
  --allow-destructive       允许捕获删除、保存、提交等高风险点击
  --max-actions <数量>      每个路由最多捕获的操作数，默认 40
  --wait-ms <毫秒>          点击后等待页面稳定，默认 500
  --screenshots             保存路由和点击后的截图
  --browser <类型>          chromium、firefox 或 webkit，默认 chromium
  --output-dir <目录>       指定输出目录
`);
}

function timestamp() {
  const now = new Date();
  const pad = value => String(value).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

function listSourceFiles(root) {
  const result = [];
  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (entry.name.startsWith('.') || IGNORED_DIRS.has(entry.name)) continue;
      const absolute = path.join(directory, entry.name);
      if (entry.isDirectory()) walk(absolute);
      else if (SOURCE_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) result.push(absolute);
    }
  }
  walk(root);
  return result.sort();
}

function matchingEnd(text, start, open, close) {
  let depth = 0;
  let quote = null;
  let escaped = false;
  for (let index = start; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (quote) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === quote) quote = null;
      continue;
    }
    if (char === '"' || char === "'" || char === '`') {
      quote = char;
      continue;
    }
    if (char === '/' && next === '/') {
      const newline = text.indexOf('\n', index + 2);
      index = newline === -1 ? text.length : newline;
      continue;
    }
    if (char === '/' && next === '*') {
      const end = text.indexOf('*/', index + 2);
      index = end === -1 ? text.length : end + 1;
      continue;
    }
    if (char === open) depth += 1;
    else if (char === close) {
      depth -= 1;
      if (depth === 0) return index;
    }
  }
  return -1;
}

function propertyText(objectText, name) {
  const match = new RegExp(`(?:^|[,\\n])\\s*${name}\\s*:\\s*`, 'm').exec(objectText);
  if (!match) return null;
  const start = match.index + match[0].length;
  let end = start;
  let quote = null;
  let brace = 0;
  let bracket = 0;
  let paren = 0;
  for (; end < objectText.length; end += 1) {
    const char = objectText[end];
    if (quote) {
      if (char === quote && objectText[end - 1] !== '\\') quote = null;
      continue;
    }
    if (char === '"' || char === "'" || char === '`') quote = char;
    else if (char === '{') brace += 1;
    else if (char === '}') brace -= 1;
    else if (char === '[') bracket += 1;
    else if (char === ']') bracket -= 1;
    else if (char === '(') paren += 1;
    else if (char === ')') paren -= 1;
    else if (char === ',' && brace === 0 && bracket === 0 && paren === 0) break;
  }
  return objectText.slice(start, end).trim();
}

function stringValue(value) {
  return String(value || '').match(/^["'`]([^"'`]*)["'`]/)?.[1] || null;
}

function extractObjects(arrayText) {
  const objects = [];
  for (let index = 0; index < arrayText.length;) {
    if (arrayText[index] !== '{') {
      index += 1;
      continue;
    }
    const end = matchingEnd(arrayText, index, '{', '}');
    if (end === -1) break;
    objects.push(arrayText.slice(index + 1, end));
    index = end + 1;
  }
  return objects;
}

function findRouteArrays(text) {
  const arrays = [];
  for (const pattern of [/\broutes\s*:\s*\[/g, /\b(?:const|let|var)\s+routes\s*=\s*\[/g]) {
    for (const match of text.matchAll(pattern)) {
      const start = text.indexOf('[', match.index);
      const end = matchingEnd(text, start, '[', ']');
      if (end !== -1) arrays.push(text.slice(start + 1, end));
    }
  }
  return arrays;
}

function discoverRoutes(projectDir) {
  const files = listSourceFiles(projectDir);
  const routeFile = files.find(file => /createRouter|routes\s*[:=]/.test(readText(file)));
  if (!routeFile) return { routeFile: null, routes: [], skipped: [] };
  const text = readText(routeFile);
  const routes = [];
  function visit(arrayText, parentPath = '') {
    for (const objectText of extractObjects(arrayText)) {
      const routePath = stringValue(propertyText(objectText, 'path'));
      if (!routePath) continue;
      const fullPath = routePath.startsWith('/')
        ? routePath
        : `${parentPath.replace(/\/$/, '')}/${routePath}`.replace(/\/+/g, '/');
      routes.push({ path: fullPath || '/', routeFile });
      const childrenValue = propertyText(objectText, 'children');
      if (childrenValue?.startsWith('[')) {
        const end = matchingEnd(childrenValue, 0, '[', ']');
        if (end !== -1) visit(childrenValue.slice(1, end), fullPath);
      }
    }
  }
  for (const array of findRouteArrays(text)) visit(array);
  const seen = new Set();
  const unique = routes.filter(route => {
    if (seen.has(route.path)) return false;
    seen.add(route.path);
    return true;
  });
  return {
    routeFile,
    routes: unique.filter(route => !route.path.includes(':') && !route.path.includes('*')),
    skipped: unique.filter(route => route.path.includes(':') || route.path.includes('*')),
  };
}

function readPlaywrightConfig(projectDir) {
  const candidates = ['playwright.config.ts', 'playwright.config.js', 'playwright.config.mjs', 'playwright.config.cjs'];
  const configFile = candidates.map(name => path.join(projectDir, name)).find(fs.existsSync) || null;
  const text = configFile ? readText(configFile) : '';
  const baseUrl = text.match(/(?:baseURL\s*[:=]|const\s+baseURL\s*=)\s*["']([^"']+)["']/)?.[1] || null;
  const channel = text.match(/channel\s*:\s*["']([^"']+)["']/)?.[1] || null;
  const executablePath = text.match(/executablePath\s*:\s*["']([^"']+)["']/)?.[1] || null;
  const hasWebServer = /\bwebServer\s*:/.test(text);
  return { configFile, baseUrl, channel, executablePath, hasWebServer };
}

function safeName(value) {
  return String(value || 'element').replace(/\s+/g, ' ').trim().slice(0, 80) || 'element';
}

function normalizePath(urlValue) {
  try {
    return new URL(urlValue).pathname;
  } catch {
    return urlValue;
  }
}

function escapeRegex(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function locatorCode(action) {
  const target = action.target;
  let code;
  if (target.testId) code = `page.getByTestId(${JSON.stringify(target.testId)})`;
  else if (target.role && target.name) code = `page.getByRole(${JSON.stringify(target.role)}, { name: ${JSON.stringify(target.name)}, exact: true })`;
  else if (target.id) code = `page.locator(${JSON.stringify(`#${target.id}`)})`;
  else code = `page.locator(${JSON.stringify(target.css || 'button')}).nth(${target.index || 0})`;
  return code;
}

async function loginWithCredentials(browser, options) {
  if (!options.loginUsername && !options.loginPassword) return null;
  if (!options.loginUsername || !options.loginPassword) fail('--login-username 与 --login-password 必须同时提供。');
  const context = await browser.newContext({ baseURL: options.baseUrl });
  const page = await context.newPage();
  try {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.locator('#login-username').fill(options.loginUsername);
    await page.locator('#login-password').fill(options.loginPassword);
    await page.locator('button[type="submit"]').click();
    await page.locator('#login-username').waitFor({ state: 'hidden', timeout: 30000 });
    return await context.storageState();
  } catch (error) {
    const message = await page.locator('.error-alert').first().textContent().catch(() => '');
    throw new Error(`登录失败${message ? `: ${message.trim()}` : ''}；${error.message}`);
  } finally {
    await page.close();
    await context.close();
  }
}

async function collectActions(page, allowDestructive) {
  const raw = await page.locator('button, a[href], [role="button"], [role="link"], input[type="button"], input[type="submit"]')
    .evaluateAll(elements => elements.map((element, index) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      const visible = style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
      const tag = element.tagName.toLowerCase();
      const role = element.getAttribute('role') || (tag === 'a' ? 'link' : 'button');
      const name = element.getAttribute('aria-label') || element.getAttribute('title') || element.innerText?.trim() || element.value || element.getAttribute('href') || '';
      const className = [...element.classList].filter(Boolean).join('.');
      return {
        index,
        visible,
        disabled: element.hasAttribute('disabled') || element.getAttribute('aria-disabled') === 'true',
        role,
        name,
        testId: element.getAttribute('data-testid'),
        id: element.id || null,
        css: className ? `.${className}` : null,
      };
    }));
  const seen = new Set();
  return raw.filter(item => {
    if (!item.visible || item.disabled || !item.name) return false;
    const key = `${item.role}|${item.name}|${item.testId || ''}|${item.id || ''}`;
    if (seen.has(key)) return false;
    seen.add(key);
    item.risky = RISKY_WORDS.test(item.name);
    return allowDestructive || !item.risky;
  });
}

function loadPlaywright(projectDir) {
  try {
    return createRequire(path.join(projectDir, 'package.json'))('playwright');
  } catch {
    try {
      return createRequire(path.join(projectDir, 'package.json'))('@playwright/test');
    } catch {
      fail('目标工程未发现本地 playwright 或 @playwright/test 依赖，请先安装项目依赖。');
    }
  }
}

function waitForServer(baseUrl, timeoutMs = 30000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const response = await fetch(baseUrl);
        if (response.status < 500) return resolve();
      } catch {}
      if (Date.now() - started >= timeoutMs) return reject(new Error(`服务未在 ${timeoutMs}ms 内可访问: ${baseUrl}`));
      setTimeout(poll, 500);
    };
    poll();
  });
}

function sourceLanguage(projectDir) {
  return fs.existsSync(path.join(projectDir, 'playwright.config.ts')) || fs.existsSync(path.join(projectDir, 'tsconfig.json')) ? 'ts' : 'js';
}

function writeSpec(route, capture, outputDir, language) {
  const title = `捕获 ${route.path}`;
  const lines = language === 'ts'
    ? ["import { test, expect } from '@playwright/test';", '', `const route = ${JSON.stringify(route.path)};`, '', `test.describe(${JSON.stringify(title)}, () => {`]
    : [`const { test, expect } = require('@playwright/test');`, '', `const route = ${JSON.stringify(route.path)};`, '', `test.describe(${JSON.stringify(title)}, () => {`];
  if (capture.observedPath) {
    lines.push(`  test(${JSON.stringify(`访问${route.path}`)}, async ({ page }) => {`);
    lines.push('    await page.goto(route);');
    lines.push(`    await expect(page).toHaveURL(new RegExp(${JSON.stringify(escapeRegex(capture.observedPath))}));`);
    lines.push('  });', '');
  }
  for (const [index, action] of capture.actions.entries()) {
    lines.push(`  test(${JSON.stringify(`点击${action.name || '控件'} (${index + 1})`)}, async ({ page }) => {`);
    lines.push('    await page.goto(route);');
    lines.push(`    await ${locatorCode(action)}.click();`);
    if (action.observedPath && action.observedPath !== capture.initialPath) {
      lines.push(`    await expect(page).toHaveURL(new RegExp(${JSON.stringify(escapeRegex(action.observedPath))}));`);
    }
    if (action.dialogVisible) lines.push("    await expect(page.getByRole('dialog').first()).toBeVisible();");
    lines.push('  });', '');
  }
  lines.push('});', '');
  const fileName = `${String(route.index).padStart(3, '0')}-${route.path === '/' ? 'root' : route.path.slice(1).replace(/[^\p{L}\p{N}_-]+/gu, '-').replace(/^-+|-+$/g, '') || 'page'}.spec.${language}`;
  const file = path.join(outputDir, fileName);
  fs.writeFileSync(file, lines.join('\n'), 'utf8');
  return fileName;
}

async function captureRoute(browser, route, options, outputDir) {
  const contextOptions = { baseURL: options.baseUrl };
  if (options.storageState) contextOptions.storageState = options.storageState;
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();
  const result = { path: route.path, initialPath: null, observedPath: null, actions: [], skipped_actions: [], errors: [] };
  try {
    await page.goto(route.path, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(options.waitMs);
    result.initialPath = normalizePath(page.url());
    result.observedPath = result.initialPath;
    if (options.screenshots) await page.screenshot({ path: path.join(outputDir, `route-${route.index}-initial.png`), fullPage: true });
    const actions = await collectActions(page, options.allowDestructive);
    for (const action of actions.slice(0, options.maxActions)) {
      const descriptor = { ...action, name: safeName(action.name) };
      const actionPage = await context.newPage();
      try {
        await actionPage.goto(route.path, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await actionPage.waitForTimeout(options.waitMs);
        const locator = action.testId
          ? actionPage.getByTestId(action.testId)
          : action.role && action.name
            ? actionPage.getByRole(action.role, { name: action.name, exact: true })
            : action.id
              ? actionPage.locator(`#${action.id}`)
              : actionPage.locator(action.css || 'button').nth(action.index || 0);
        await locator.scrollIntoViewIfNeeded();
        await locator.click({ timeout: 10000 });
        await actionPage.waitForTimeout(options.waitMs);
        const observedPath = normalizePath(actionPage.url());
        const dialogVisible = await actionPage.getByRole('dialog').count() > 0;
        result.actions.push({
          name: action.name,
          risky: action.risky,
          target: { role: action.role, name: action.name, testId: action.testId, id: action.id, css: action.css, index: action.index },
          observedPath,
          dialogVisible,
        });
        if (options.screenshots) await actionPage.screenshot({ path: path.join(outputDir, `route-${route.index}-action-${result.actions.length}.png`), fullPage: true });
      } catch (error) {
        result.errors.push({ action: action.name, message: error.message });
      } finally {
        await actionPage.close();
      }
    }
    if (actions.length > options.maxActions) result.skipped_actions.push({ reason: `超过 max-actions=${options.maxActions}`, count: actions.length - options.maxActions });
  } catch (error) {
    result.errors.push({ message: error.message });
  } finally {
    await page.close();
    await context.close();
  }
  return result;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) return printHelp();
  if (!args.projectDir) fail('请使用 --project-dir 指定前端工程。');
  const projectDir = path.resolve(args.projectDir);
  if (!fs.existsSync(projectDir) || !fs.statSync(projectDir).isDirectory()) fail(`工程目录不存在: ${projectDir}`);
  if (!Number.isInteger(args.maxActions) || args.maxActions < 1) fail('--max-actions 必须是正整数。');
  const outputDir = path.resolve(args.outputDir || path.join(projectDir, 'tests', 'playwright-tester-create', timestamp()));
  fs.mkdirSync(outputDir, { recursive: true });
  const config = readPlaywrightConfig(projectDir);
  const baseUrl = args.baseUrl || config.baseUrl;
  if (!baseUrl) fail('未找到 baseURL，请通过 --base-url 指定业务系统地址。');
  const discovery = discoverRoutes(projectDir);
  const routes = args.routes.length
    ? args.routes.map(routePath => ({ path: routePath, routeFile: discovery.routeFile }))
    : discovery.routes;
  if (!routes.length) fail('未发现可访问的静态路由。');
  routes.forEach((route, index) => { route.index = index + 1; });
  let server = null;
  const warnings = [];
  if (config.executablePath && !fs.existsSync(config.executablePath)) warnings.push(`Playwright executablePath 不存在，已忽略: ${config.executablePath}`);
  if (config.hasWebServer && !args.startCommand) warnings.push('检测到 webServer 配置；capture 不自动执行配置中的命令，请确认服务已运行或传入 --start-command。');
  try {
    if (args.startCommand) {
      server = spawn(args.startCommand, { cwd: projectDir, shell: true, stdio: 'inherit' });
      await waitForServer(baseUrl);
    } else {
      await waitForServer(baseUrl, 5000).catch(error => { throw new Error(`${error.message}；请先启动服务或传入 --start-command。`); });
    }
    const playwright = loadPlaywright(projectDir);
    const browserType = playwright[args.browser || 'chromium'];
    if (!browserType) fail(`不支持的浏览器类型: ${args.browser}`);
    const launchOptions = { headless: !args.headed };
    const browserName = args.browser || 'chromium';
    if (browserName === 'chromium' && config.channel && fs.existsSync(config.executablePath || '')) launchOptions.executablePath = config.executablePath;
    else if (browserName === 'chromium' && config.channel) launchOptions.channel = config.channel;
    const browser = await browserType.launch(launchOptions);
    const loginStorageState = await loginWithCredentials(browser, {
      ...args,
      baseUrl,
    });
    const captures = [];
    for (const route of routes) {
      const capture = await captureRoute(browser, route, {
        ...args,
        baseUrl,
        storageState: loginStorageState || (args.storageState ? path.resolve(projectDir, args.storageState) : null),
      }, outputDir);
      captures.push(capture);
    }
    await browser.close();
    const language = sourceLanguage(projectDir);
    const generated = [];
    for (const [index, capture] of captures.entries()) {
      if (capture.actions.length || capture.observedPath) generated.push(writeSpec({ ...routes[index], index: index + 1 }, capture, outputDir, language));
    }
    const report = {
      generated_at: new Date().toISOString(),
      project_dir: projectDir,
      base_url: baseUrl,
      route_file: discovery.routeFile,
      route_order: routes.map(route => route.path),
      skipped_dynamic_routes: discovery.skipped,
      warnings,
      safe_mode: !args.allowDestructive,
      generated_files: generated,
      captures,
    };
    fs.writeFileSync(path.join(outputDir, 'capture-report.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
    console.log(JSON.stringify({ output_dir: outputDir, generated, warnings, skipped_dynamic_routes: discovery.skipped }, null, 2));
  } finally {
    if (server && !server.killed) server.kill('SIGTERM');
  }
}

main().catch(error => fail(error.message));
