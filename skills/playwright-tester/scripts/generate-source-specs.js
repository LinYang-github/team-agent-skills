#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const { parseBusinessContracts } = require('./business-contracts');

const SOURCE_EXTENSIONS = new Set(['.js', '.jsx', '.ts', '.tsx', '.vue']);
const IGNORED_DIRS = new Set(['.git', 'node_modules', 'dist', 'build', 'coverage', 'playwright-tester-create']);

function fail(message) {
  console.error(message);
  process.exit(1);
}

function parseArgs(argv) {
  const args = { projectDir: null, outputDir: null, contractDir: null, help: false };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === '--help' || value === '-h') args.help = true;
    else if (value === '--project-dir') args.projectDir = argv[++index];
    else if (value === '--output-dir') args.outputDir = argv[++index];
    else if (value === '--contract-dir') args.contractDir = argv[++index];
    else fail(`未知参数: ${value}`);
  }
  return args;
}

function printHelp() {
  console.log(`用法:
  node scripts/generate-source-specs.js --project-dir <前端子目录> [--output-dir <输出根目录>] [--contract-dir <契约目录>]

说明:
  只做源码静态分析，按 Vue Router 路由顺序生成页面级 *.spec.js/*.spec.ts。
  如果存在 src/test-contracts/**/*.scenario.{json,js,ts}，优先按业务场景契约生成。
  默认输出到 <project>/tests/playwright-tester-create/YYYYMMDD-HHmmss/。
`);
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

function readText(file) {
  try {
    return fs.readFileSync(file, 'utf8');
  } catch {
    return '';
  }
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
    if (char === '"' || char === "'" || char === '`') {
      quote = char;
      continue;
    }
    if (char === open) depth += 1;
    if (char === close) {
      depth -= 1;
      if (depth === 0) return index;
    }
  }
  return -1;
}

function extractDelimited(text, start, open, close) {
  const end = matchingEnd(text, start, open, close);
  return end === -1 ? null : { value: text.slice(start + 1, end), end };
}

function splitTopLevel(text) {
  const parts = [];
  let start = 0;
  let brace = 0;
  let bracket = 0;
  let paren = 0;
  let quote = null;
  let escaped = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
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
    if (char === '{') brace += 1;
    else if (char === '}') brace -= 1;
    else if (char === '[') bracket += 1;
    else if (char === ']') bracket -= 1;
    else if (char === '(') paren += 1;
    else if (char === ')') paren -= 1;
    else if (char === ',' && brace === 0 && bracket === 0 && paren === 0) {
      parts.push(text.slice(start, index));
      start = index + 1;
    }
  }
  if (text.slice(start).trim()) parts.push(text.slice(start));
  return parts;
}

function extractObjects(arrayText) {
  const objects = [];
  let index = 0;
  while (index < arrayText.length) {
    if (arrayText[index] !== '{') {
      index += 1;
      continue;
    }
    const extracted = extractDelimited(arrayText, index, '{', '}');
    if (!extracted) break;
    objects.push(extracted.value);
    index = extracted.end + 1;
  }
  return objects;
}

function propertyText(objectText, name) {
  const pattern = new RegExp(`(?:^|[,\\n])\\s*${name}\\s*:\\s*`, 'm');
  const match = pattern.exec(objectText);
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
  const match = String(value || '').match(/^["'`]([^"'`]*)["'`]/);
  return match ? match[1] : null;
}

function findRouteArrays(text) {
  const arrays = [];
  const patterns = [
    /\broutes\s*:\s*\[/g,
    /\b(?:const|let|var)\s+routes\s*=\s*\[/g,
    /\bexport\s+default\s*\[/g,
  ];
  for (const pattern of patterns) {
    for (const match of text.matchAll(pattern)) {
      const start = text.indexOf('[', match.index);
      const extracted = extractDelimited(text, start, '[', ']');
      if (extracted) arrays.push(extracted.value);
    }
  }
  return arrays;
}

function collectImports(text) {
  const imports = new Map();
  for (const match of text.matchAll(/\bimport\s+([A-Za-z_$][\w$]*)\s+from\s+["']([^"']+)["']/g)) {
    imports.set(match[1], match[2]);
  }
  for (const match of text.matchAll(/\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*[^\n;]*?import\(\s*["']([^"']+)["']\s*\)/g)) {
    imports.set(match[1], match[2]);
  }
  return imports;
}

function resolveImport(fromFile, importPath) {
  if (!importPath || !importPath.startsWith('.')) return null;
  const base = path.resolve(path.dirname(fromFile), importPath);
  const candidates = [base, ...Array.from(SOURCE_EXTENSIONS, extension => `${base}${extension}`), ...Array.from(SOURCE_EXTENSIONS, extension => path.join(base, `index${extension}`))];
  return candidates.find(candidate => fs.existsSync(candidate) && fs.statSync(candidate).isFile()) || null;
}

function routeEntries(routeFile, imports, arrayText, parentPath = '') {
  const entries = [];
  for (const objectText of extractObjects(arrayText)) {
    const routePath = stringValue(propertyText(objectText, 'path'));
    if (!routePath) continue;
    const fullPath = routePath.startsWith('/') ? routePath : `${parentPath.replace(/\/$/, '')}/${routePath}`.replace(/\/+/g, '/');
    const componentValue = propertyText(objectText, 'component') || '';
    const directImport = componentValue.match(/import\(\s*["']([^"']+)["']\s*\)/)?.[1];
    const componentName = componentValue.match(/^([A-Za-z_$][\w$]*)/)?.[1];
    const componentPath = resolveImport(routeFile, directImport || imports.get(componentName));
    const childrenValue = propertyText(objectText, 'children');
    const children = childrenValue && childrenValue.startsWith('[')
      ? extractDelimited(childrenValue, 0, '[', ']')?.value
      : null;
    const routeName = children ? null : stringValue(propertyText(objectText, 'name'));
    if (componentPath) entries.push({ path: fullPath, name: routeName, componentPath, routeFile });
    if (children) entries.push(...routeEntries(routeFile, imports, children, fullPath));
  }
  return entries;
}

function findRoutes(files) {
  const routes = [];
  for (const file of files) {
    const text = readText(file);
    if (!/createRouter|routes\s*[:=]/.test(text)) continue;
    const imports = collectImports(text);
    for (const arrayText of findRouteArrays(text)) routes.push(...routeEntries(file, imports, arrayText));
  }
  const seen = new Set();
  return routes.filter(route => {
    const key = `${route.path}|${route.componentPath}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function collectDependencies(entryFile) {
  const files = [];
  const visited = new Set();
  function visit(file) {
    if (!file || visited.has(file)) return;
    visited.add(file);
    const text = readText(file);
    files.push({ file, text });
    const imports = collectImports(text);
    for (const importPath of imports.values()) visit(resolveImport(file, importPath));
  }
  visit(entryFile);
  return files;
}

function cleanText(value) {
  return String(value || '').replace(/\s+/g, ' ').replace(/<!--.*?-->/g, '').trim();
}

function loadTranslations(projectDir) {
  const localeFile = path.join(projectDir, 'src', 'i18n', 'locales', 'cn.js');
  const text = readText(localeFile);
  if (!text) return {};
  const translations = {};
  const stack = [];
  for (const line of text.split(/\r?\n/)) {
    const indent = line.match(/^\s*/)?.[0].length || 0;
    while (stack.length && stack[stack.length - 1].indent >= indent) stack.pop();
    const objectMatch = line.match(/^\s*([A-Za-z_$][\w$]*)\s*:\s*\{\s*$/);
    if (objectMatch) {
      stack.push({ key: objectMatch[1], indent });
      continue;
    }
    const valueMatch = line.match(/^\s*([A-Za-z_$][\w$]*)\s*:\s*(['"])((?:\\.|(?!\2).)*)\2\s*,?\s*$/);
    if (!valueMatch) continue;
    const value = valueMatch[3].replace(/\\(['"])/g, '$1');
    translations[[...stack.map(item => item.key), valueMatch[1]].join('.')] = value;
  }
  return translations;
}

function translatedLabel(value, translations) {
  const matches = [...String(value || '').matchAll(/\bt\(\s*['"]([^'"]+)['"]\s*\)/g)];
  if (matches.length !== 1) return null;
  const key = matches[0][1];
  const withoutExpression = String(value || '')
    .replace(/<!--.*?-->/gs, '')
    .replace(/\{\{[\s\S]*?\}\}/g, ' ')
    .replace(/<[^>]*>/g, ' ')
    .replace(/\bt\(\s*['"][^'"]+['"]\s*\)/g, ' ');
  if (cleanText(withoutExpression)) return null;
  return translations[key] || null;
}

function literalLabel(value, translations = {}) {
  const translated = translatedLabel(value, translations);
  if (translated) return translated;
  const withoutVueExpressions = String(value || '')
    .replace(/<!--.*?-->/gs, '')
    .replace(/\{\{[\s\S]*?\}\}/g, ' ')
    .replace(/<[^>]*>/g, ' ');
  const label = cleanText(withoutVueExpressions);
  if (!label || label.length > 80 || /[{}<>]|\b(?:t|i18n|String|format|computed)\s*\(/.test(label)) return null;
  return label;
}

function literalAttribute(attributes, names, translations = {}) {
  const namePattern = names.join('|');
  const match = String(attributes || '').match(new RegExp(`(?:^|\\s)(:)?(?:${namePattern})\\s*=\\s*(["'])(.*?)\\2`, 'i'));
  if (!match) return null;
  return match[1] ? translatedLabel(match[3], translations) : literalLabel(match[3], translations);
}

function findMatchingTag(text, start, tagName) {
  const pattern = new RegExp(`<\\/?${tagName}\\b[^>]*>`, 'gi');
  pattern.lastIndex = start;
  let depth = 1;
  let match;
  while ((match = pattern.exec(text))) {
    if (/^<\//.test(match[0])) {
      depth -= 1;
      if (depth === 0) return { start: match.index, end: pattern.lastIndex };
    } else if (!/\/\s*>$/.test(match[0])) {
      depth += 1;
    }
  }
  return null;
}

function extractControls(text) {
  const controls = [];
  const pattern = /<(button|el-button|a|router-link|el-link)\b([^>]*)>/gi;
  let match;
  while ((match = pattern.exec(text))) {
    const closing = findMatchingTag(text, pattern.lastIndex, match[1]);
    if (!closing) continue;
    controls.push({ tag: match[1], attributes: match[2], body: text.slice(pattern.lastIndex, closing.start) });
    pattern.lastIndex = closing.end;
  }
  return controls;
}

function extractClickableElements(text) {
  const elements = [];
  const pattern = /<(div|span|li)\b([^>]*?(?:@click|v-on:click)\s*=\s*[^>]*)>/gi;
  const indexes = new Map();
  let match;
  while ((match = pattern.exec(text))) {
    const closing = findMatchingTag(text, pattern.lastIndex, match[1]);
    if (!closing) continue;
    const className = literalAttribute(match[2], ['class']);
    if (className) {
      const selectorClass = className.split(/\s+/)[0];
      const index = indexes.get(selectorClass) || 0;
      indexes.set(selectorClass, index + 1);
      elements.push({ tag: match[1], attributes: match[2], body: text.slice(pattern.lastIndex, closing.start), className, index });
    }
    pattern.lastIndex = closing.end;
  }
  return elements;
}

function quote(value) {
  return JSON.stringify(value);
}

function addLocatorIndex(expression, target) {
  if (Number.isInteger(target?.index)) return `${expression}.nth(${target.index})`;
  if (target?.first === true) return `${expression}.first()`;
  return expression;
}

function contractLocator(target, translations) {
  if (!target || typeof target !== 'object') throw new Error('target 必须是对象');
  if (target.testId) return addLocatorIndex(`page.getByTestId(${quote(target.testId)})`, target);
  if (target.css) return addLocatorIndex(`page.locator(${quote(target.css)})`, target);
  if (target.placeholder || target.placeholderKey) {
    const value = target.placeholder || translations[target.placeholderKey];
    if (!value) throw new Error(`无法解析 placeholder 文案: ${target.placeholderKey || ''}`);
    return addLocatorIndex(`page.getByPlaceholder(${quote(value)})`, target);
  }
  if (target.label || target.labelKey) {
    const value = target.label || translations[target.labelKey];
    if (!value) throw new Error(`无法解析 label 文案: ${target.labelKey || ''}`);
    return addLocatorIndex(`page.getByLabel(${quote(value)})`, target);
  }
  if (target.text || target.textKey) {
    const value = target.text || translations[target.textKey];
    if (!value) throw new Error(`无法解析文本: ${target.textKey || ''}`);
    const exact = target.exact === undefined ? true : Boolean(target.exact);
    return addLocatorIndex(`page.getByText(${quote(value)}, { exact: ${exact} })`, target);
  }
  if (target.role) {
    const name = target.name || (target.nameKey ? translations[target.nameKey] : null);
    if (target.nameKey && !name) throw new Error(`无法解析 role 文案: ${target.nameKey}`);
    const options = name ? `, { name: ${quote(name)}${target.exact === true ? ', exact: true' : ''} }` : '';
    return addLocatorIndex(`page.getByRole(${quote(target.role)}${options})`, target);
  }
  throw new Error('target 缺少 testId、css、placeholder、label、text 或 role');
}

function contractValue(value, lines, declaredValues) {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return quote(value);
  if (!value || typeof value !== 'object') throw new Error('value 必须是静态值、env 或 generator 对象');
  if (value.env) return `process.env[${quote(value.env)}]`;
  if (value.generator === 'uniqueUsername') {
    const variable = value.name || 'uniqueUsername';
    if (!declaredValues.has(variable)) {
      lines.push(`    const ${variable} = ${quote(value.prefix || 'test_')} + Date.now();`);
      declaredValues.add(variable);
    }
    return variable;
  }
  throw new Error('不支持的 value 来源');
}

function responsePredicate(waitFor) {
  if (!waitFor || typeof waitFor !== 'object' || !waitFor.method || !waitFor.path) {
    throw new Error('waitFor 必须包含 method 和 path');
  }
  const pathPattern = String(waitFor.path).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const predicates = [
    `response.request().method() === ${quote(waitFor.method)}`,
    `/${pathPattern}/.test(url.pathname)`,
  ];
  for (const [key, value] of Object.entries(waitFor.query || {})) {
    predicates.push(`url.searchParams.get(${quote(key)}) === ${quote(value)}`);
  }
  if (waitFor.status === 'ok') predicates.push('response.ok()');
  return `page.waitForResponse((response) => {\n      const url = new URL(response.url());\n      return ${predicates.join(' && ')};\n    })`;
}

function renderContractAction(action, lines, translations, context) {
  if (action.action === 'navigate') {
    if (!action.route) throw new Error('navigate 缺少 route');
    lines.push(`    await page.goto(${quote(action.route)});`);
    return;
  }
  const locator = contractLocator(action.target, translations);
  let responseVariable = null;
  if (action.waitFor) {
    responseVariable = `responsePromise${context.responseIndex++}`;
    lines.push(`    const ${responseVariable} = ${responsePredicate(action.waitFor)};`);
  }
  if (action.action === 'click') lines.push(`    await ${locator}.click();`);
  else if (action.action === 'fill') lines.push(`    await ${locator}.fill(${contractValue(action.value, lines, context.declaredValues)});`);
  else if (action.action === 'select') lines.push(`    await ${locator}.selectOption(${contractValue(action.value, lines, context.declaredValues)});`);
  else if (action.action === 'check') lines.push(`    await ${locator}.check();`);
  else if (action.action === 'uncheck') lines.push(`    await ${locator}.uncheck();`);
  else if (action.action === 'press') lines.push(`    await ${locator}.press(${quote(action.key || 'Enter')});`);
  if (responseVariable) lines.push(`    await ${responseVariable};`);
}

function renderContractAssertion(effect, lines, translations) {
  if (effect.assertion === 'url') {
    const value = effect.value || effect.path;
    if (!value) throw new Error('url 断言缺少 value 或 path');
    lines.push(`    await expect(page).toHaveURL(new RegExp(${quote(String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))}));`);
    return;
  }
  const locator = contractLocator(effect.target, translations);
  if (effect.assertion === 'visible' || effect.assertion === 'row-exists') lines.push(`    await expect(${locator}).toBeVisible();`);
  else if (effect.assertion === 'hidden' || effect.assertion === 'row-disappears') lines.push(`    await expect(${locator}).toBeHidden();`);
  else if (effect.assertion === 'text') lines.push(`    await expect(${locator}).toContainText(${quote(effect.value || '')});`);
  else if (effect.assertion === 'value') lines.push(`    await expect(${locator}).toHaveValue(${quote(effect.value || '')});`);
  else if (effect.assertion === 'checked') lines.push(`    await expect(${locator}).toBeChecked();`);
}

function contractSpecForScenario(route, contract, scenario, analysis, translations) {
  const lines = [
    `const { test, expect } = require(${quote('playwright/test')});`,
    '',
    `const route = ${quote(scenario.route || route.path)};`,
    '',
    `test.describe(${quote(scenario.title)}, () => {`,
    `  test(${quote(scenario.title)}, async ({ page }) => {`,
    `    // 业务场景契约: ${path.basename(contract.file)}:${scenario.sourceLine || contract.sourceLine}`,
  ];
  const context = { declaredValues: new Set(), responseIndex: 1 };
  try {
    for (const action of [...(scenario.preconditions || []), ...(scenario.steps || [])]) renderContractAction(action, lines, translations, context);
    for (const effect of scenario.effects || []) renderContractAssertion(effect, lines, translations);
  } catch (error) {
    return { error: error.message };
  }
  lines.push('  });', '});', '');
  return { text: lines.join('\n'), featureCount: (scenario.preconditions || []).length + (scenario.steps || []).length + (scenario.effects || []).length };
}

function analyzeRoute(route, projectDir) {
  if (route.path.includes(':') || route.path.includes('*')) {
    return { features: [], reason: '动态路由参数无法从源码确定' };
  }
  const sources = collectDependencies(route.componentPath);
  const combined = sources.map(item => item.text).join('\n');
  const vueTemplate = sources.find(item => path.extname(item.file) === '.vue')?.text || combined;
  const translations = loadTranslations(projectDir);
  const features = [];
  const seen = new Set();
  const hasSubmitHandler = /<form\b[^>]*(?:@submit(?:\.[\w-]+)*|v-on:submit(?:\.[\w-]+)*)\s*=/.test(vueTemplate);
  function add(feature) {
    const key = JSON.stringify(feature);
    if (!seen.has(key)) {
      seen.add(key);
      features.push(feature);
    }
  }

  for (const control of extractControls(vueTemplate)) {
    const { tag, attributes, body } = control;
    const label = literalLabel(body, translations) || literalAttribute(attributes, ['aria-label', 'title', 'label'], translations);
    if (!label) continue;
    const click = /(?:@click|v-on:click)\s*=/.test(attributes);
    const target = literalAttribute(attributes, ['to'], translations);
    if (target) add({ kind: 'link', label, target });
    else if (click || (hasSubmitHandler && /\btype\s*=\s*["']submit["']/i.test(attributes))) {
      add({ kind: 'click', label, role: /^(a|router-link|el-link)$/i.test(tag) ? 'link' : 'button' });
    }
  }

  const fieldPattern = /<(input|textarea|select|el-input-number|el-input|el-select|el-date-picker|el-switch|el-checkbox|el-radio)\b([^>]*)>/gi;
  for (const match of vueTemplate.matchAll(fieldPattern)) {
    const [, tag, attributes] = match;
    const label = literalAttribute(attributes, ['aria-label', 'placeholder', 'title', 'label'], translations);
    if (label) {
      const role = /select|date-picker/i.test(tag) ? 'combobox' : /input-number/i.test(tag) ? 'spinbutton' : /switch/i.test(tag) ? 'switch' : /checkbox/i.test(tag) ? 'checkbox' : /radio/i.test(tag) ? 'radio' : 'textbox';
      add({ kind: 'field', label, role });
    }
  }

  for (const element of extractClickableElements(vueTemplate)) {
    const label = literalLabel(element.body, translations) || element.className;
    add({ kind: 'click', label, role: 'locator', selector: `.${element.className.split(/\s+/)[0]}`, index: element.index });
  }

  const hasLifecycleLoad = /\bonMounted\s*\(|\bmounted\s*\(|\bcreated\s*\(/.test(combined) && /\b(fetch|axios|\$http|service\.|api\.)/.test(combined);
  if (hasLifecycleLoad && /<(table|el-table|ul|ol)\b|\bv-for\s*=/.test(vueTemplate)) {
    add({ kind: 'load', selector: /<(table|el-table)\b/.test(vueTemplate) ? 'table' : 'list' });
  }

  const language = sources.some(item => /<script[^>]*\blang=["']ts["']/.test(item.text) || /\.(ts|tsx)$/.test(item.file)) ? 'ts' : 'js';
  return { features, language, sourceFiles: sources.map(item => item.file) };
}

function specForRoute(route, analysis, title) {
  const lines = [
    `const { test, expect } = require(${quote(analysis.language === 'ts' ? 'playwright/test' : 'playwright/test')});`,
    '',
    `const route = ${quote(route.path)};`,
    '',
    `test.describe(${quote(title)}, () => {`,
  ];
  for (const feature of analysis.features) {
    if (feature.kind === 'load') {
      lines.push(`  test(${quote(`进入${title}并展示数据`)}, async ({ page }) => {`);
      lines.push('    await page.goto(route);');
      if (feature.selector === 'table') {
        lines.push("    await expect(page.getByRole('row')).toBeVisible();");
      } else {
        lines.push("    await expect(page.getByRole('list')).toBeVisible();");
      }
      lines.push('  });', '');
    } else if (feature.kind === 'field') {
      lines.push(`  test(${quote(`查看${title}的${feature.label}控件`)}, async ({ page }) => {`);
      lines.push('    await page.goto(route);');
      lines.push(`    await expect(page.getByRole(${quote(feature.role)}, { name: ${quote(feature.label)} })).toBeVisible();`);
      lines.push('  });', '');
    } else if (feature.kind === 'link') {
      lines.push(`  test(${quote(`通过${feature.label}进入${feature.target}`)}, async ({ page }) => {`);
      lines.push('    await page.goto(route);');
      lines.push(`    await page.getByRole('link', { name: ${quote(feature.label)} }).click();`);
      lines.push(`    await expect(page).toHaveURL(new RegExp(${quote(feature.target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))}));`);
      lines.push('  });', '');
    } else if (feature.kind === 'click') {
      lines.push(`  test(${quote(`点击${feature.label}${feature.role === 'link' ? '链接' : '按钮'}`)}, async ({ page }) => {`);
      lines.push('    await page.goto(route);');
      if (feature.role === 'locator') lines.push(`    await page.locator(${quote(feature.selector)}).nth(${feature.index}).click();`);
      else lines.push(`    await page.getByRole(${quote(feature.role)}, { name: ${quote(feature.label)} }).click();`);
      lines.push('  });', '');
    }
  }
  lines.push('});', '');
  return `${lines.join('\n')}`;
}

function timestamp() {
  const now = new Date();
  const pad = value => String(value).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

function slug(value) {
  return String(value).replace(/[^\p{L}\p{N}_-]+/gu, '-').replace(/^-+|-+$/g, '').toLowerCase() || 'page';
}

function detectArchitecture(projectDir) {
  const packagePath = path.join(projectDir, 'package.json');
  const packageData = fs.existsSync(packagePath) ? JSON.parse(readText(packagePath)) : {};
  const dependencies = { ...(packageData.dependencies || {}), ...(packageData.devDependencies || {}) };
  const framework = dependencies.vue ? 'Vue' : dependencies.react ? 'React' : dependencies.svelte ? 'Svelte' : 'Unknown';
  const typescript = Boolean(dependencies.typescript);
  return { framework, typescript, packageName: packageData.name || '' };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) return printHelp();
  if (!args.projectDir) fail('请使用 --project-dir 指定目标前端子目录。');
  const projectDir = path.resolve(args.projectDir);
  if (!fs.existsSync(projectDir) || !fs.statSync(projectDir).isDirectory()) fail(`目标目录不存在: ${projectDir}`);

  const files = listSourceFiles(projectDir);
  const routes = findRoutes(files);
  const contractResult = parseBusinessContracts(projectDir, args.contractDir);
  const outputRoot = path.resolve(args.outputDir || path.join(projectDir, 'tests', 'playwright-tester-create'));
  const outputDir = path.join(outputRoot, timestamp());
  fs.mkdirSync(outputDir, { recursive: true });

  const manifest = {
    generated_at: new Date().toISOString(),
    project_dir: projectDir,
    architecture: detectArchitecture(projectDir),
    business_contracts: {
      root: path.relative(projectDir, contractResult.root) || '.',
      files: contractResult.files.map(file => path.relative(projectDir, file)),
      parsed: contractResult.contracts.map(contract => ({
        file: path.relative(projectDir, contract.file),
        route: contract.route,
        scenario_count: contract.scenarios.length,
      })),
    },
    route_order: [],
    generated_files: [],
    skipped_routes: [],
    unresolved: contractResult.errors.map(item => ({
      file: path.relative(projectDir, item.file),
      errors: item.errors,
    })),
  };
  let generatedIndex = 0;
  for (const route of routes) {
    const analysis = analyzeRoute(route, projectDir);
    const routeRecord = { path: route.path, component: path.relative(projectDir, route.componentPath) };
    const routeContracts = contractResult.contracts.filter(contract => contract.route === route.path);
    if (routeContracts.length && !analysis.language) {
      manifest.unresolved.push({
        route: route.path,
        errors: ['动态路由参数无法从源码和业务契约中确定'],
      });
      manifest.skipped_routes.push({ ...routeRecord, reason: '动态路由参数无法从源码确定' });
      continue;
    }
    let generatedContractScenario = false;
    for (const contract of routeContracts) {
      for (const scenario of contract.scenarios) {
        const rendered = contractSpecForScenario(route, contract, scenario, analysis, loadTranslations(projectDir));
        if (rendered.error) {
          manifest.unresolved.push({
            file: path.relative(projectDir, contract.file),
            scenario: scenario.id,
            errors: [rendered.error],
          });
          continue;
        }
        generatedIndex += 1;
        const title = scenario.title;
        const fileName = `${String(generatedIndex).padStart(3, '0')}-${slug(route.name || path.basename(route.componentPath, path.extname(route.componentPath)))}-${slug(scenario.id)}.spec.${analysis.language}`;
        fs.writeFileSync(path.join(outputDir, fileName), rendered.text, 'utf8');
        manifest.route_order.push({
          ...routeRecord,
          scenario: scenario.id,
          spec: fileName,
          feature_count: rendered.featureCount,
          business_contract: path.relative(projectDir, contract.file),
        });
        manifest.generated_files.push(fileName);
        generatedContractScenario = true;
      }
    }
    if (generatedContractScenario) continue;
    if (analysis.features.length === 0) {
      manifest.skipped_routes.push({ ...routeRecord, reason: analysis.reason || '未发现可静态确认的功能点' });
      continue;
    }
    generatedIndex += 1;
    const title = route.name || path.basename(route.componentPath, path.extname(route.componentPath));
    const fileName = `${String(generatedIndex).padStart(3, '0')}-${slug(title)}.spec.${analysis.language}`;
    fs.writeFileSync(path.join(outputDir, fileName), specForRoute(route, analysis, title), 'utf8');
    manifest.route_order.push({ ...routeRecord, spec: fileName, feature_count: analysis.features.length });
    manifest.generated_files.push(fileName);
  }
  fs.writeFileSync(path.join(outputDir, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ output_dir: outputDir, generated: manifest.generated_files, skipped: manifest.skipped_routes }, null, 2));
}

main();
