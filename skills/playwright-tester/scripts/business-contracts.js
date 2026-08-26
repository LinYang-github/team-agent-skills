#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');

const CONTRACT_PATTERN = /\.scenario\.(json|js|ts)$/i;
const SUPPORTED_ACTIONS = new Set(['navigate', 'click', 'fill', 'select', 'check', 'uncheck', 'press']);
const SUPPORTED_ASSERTIONS = new Set(['visible', 'hidden', 'text', 'url', 'value', 'checked', 'row-exists', 'row-disappears']);

function readText(file) {
  try {
    return fs.readFileSync(file, 'utf8');
  } catch {
    return '';
  }
}

function lineAt(text, offset) {
  return text.slice(0, Math.max(0, offset)).split(/\r?\n/).length;
}

class StaticLiteralParser {
  constructor(text, offset = 0) {
    this.text = text;
    this.index = offset;
  }

  skip() {
    while (this.index < this.text.length) {
      if (/\s/.test(this.text[this.index])) {
        this.index += 1;
        continue;
      }
      if (this.text.startsWith('//', this.index)) {
        const end = this.text.indexOf('\n', this.index + 2);
        this.index = end === -1 ? this.text.length : end + 1;
        continue;
      }
      if (this.text.startsWith('/*', this.index)) {
        const end = this.text.indexOf('*/', this.index + 2);
        this.index = end === -1 ? this.text.length : end + 2;
        continue;
      }
      break;
    }
  }

  error(message) {
    throw new Error(`${message} (offset ${this.index})`);
  }

  parse() {
    this.skip();
    const value = this.parseValue();
    this.skip();
    return value;
  }

  parseValue() {
    this.skip();
    const char = this.text[this.index];
    if (char === '{') return this.parseObject();
    if (char === '[') return this.parseArray();
    if (char === '"' || char === "'") return this.parseString();
    if (this.text.startsWith('true', this.index)) {
      this.index += 4;
      return true;
    }
    if (this.text.startsWith('false', this.index)) {
      this.index += 5;
      return false;
    }
    if (this.text.startsWith('null', this.index)) {
      this.index += 4;
      return null;
    }
    const number = this.text.slice(this.index).match(/^-?\d+(?:\.\d+)?/);
    if (number) {
      this.index += number[0].length;
      return Number(number[0]);
    }
    this.error('仅允许静态对象、数组、字符串、数字、布尔值和 null');
  }

  parseString() {
    const quote = this.text[this.index++];
    let value = '';
    while (this.index < this.text.length) {
      const char = this.text[this.index++];
      if (char === quote) return value;
      if (char !== '\\') {
        value += char;
        continue;
      }
      const escaped = this.text[this.index++];
      const escapes = { n: '\n', r: '\r', t: '\t', b: '\b', f: '\f', v: '\v' };
      value += escapes[escaped] ?? escaped;
    }
    this.error('字符串未闭合');
  }

  parseKey() {
    this.skip();
    const char = this.text[this.index];
    if (char === '"' || char === "'") return this.parseString();
    const match = this.text.slice(this.index).match(/^[A-Za-z_$][\w$-]*/);
    if (!match) this.error('对象键必须是静态标识符或字符串');
    this.index += match[0].length;
    return match[0];
  }

  parseObject() {
    const result = {};
    this.index += 1;
    this.skip();
    while (this.index < this.text.length && this.text[this.index] !== '}') {
      const key = this.parseKey();
      this.skip();
      if (this.text[this.index] !== ':') this.error(`对象键 ${key} 缺少冒号`);
      this.index += 1;
      result[key] = this.parseValue();
      this.skip();
      if (this.text[this.index] === ',') {
        this.index += 1;
        this.skip();
      } else if (this.text[this.index] !== '}') {
        this.error(`对象键 ${key} 后缺少逗号`);
      }
    }
    if (this.text[this.index] !== '}') this.error('对象未闭合');
    this.index += 1;
    return result;
  }

  parseArray() {
    const result = [];
    this.index += 1;
    this.skip();
    while (this.index < this.text.length && this.text[this.index] !== ']') {
      result.push(this.parseValue());
      this.skip();
      if (this.text[this.index] === ',') {
        this.index += 1;
        this.skip();
      } else if (this.text[this.index] !== ']') {
        this.error('数组元素后缺少逗号');
      }
    }
    if (this.text[this.index] !== ']') this.error('数组未闭合');
    this.index += 1;
    return result;
  }
}

function findLiteral(text, start) {
  let index = start;
  while (index < text.length && !['{', '['].includes(text[index])) index += 1;
  if (index >= text.length) throw new Error('未找到静态对象或数组');
  return { value: new StaticLiteralParser(text, index).parse(), offset: index };
}

function parseContractFile(file) {
  const text = readText(file);
  if (!text) return { file, errors: ['文件为空或无法读取'] };
  try {
    let parsed;
    if (path.extname(file).toLowerCase() === '.json') {
      parsed = JSON.parse(text);
    } else {
      const exportMatch = /export\s+default\s*|(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*/g.exec(text);
      if (!exportMatch) throw new Error('未找到 export default 或静态变量赋值');
      parsed = findLiteral(text, exportMatch.index + exportMatch[0].length).value;
    }
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error('契约根节点必须是对象');
    return { file, text, value: parsed, sourceLine: lineAt(text, text.indexOf('{')) };
  } catch (error) {
    return { file, errors: [error.message] };
  }
}

function validateScenario(scenario, index) {
  const errors = [];
  if (!scenario || typeof scenario !== 'object' || Array.isArray(scenario)) {
    return [`scenarios[${index}] 必须是对象`];
  }
  for (const field of ['id', 'title']) {
    if (typeof scenario[field] !== 'string' || !scenario[field].trim()) errors.push(`scenarios[${index}].${field} 必须是非空字符串`);
  }
  for (const field of ['preconditions', 'steps', 'effects']) {
    if (scenario[field] !== undefined && !Array.isArray(scenario[field])) errors.push(`scenarios[${index}].${field} 必须是数组`);
  }
  for (const [stepIndex, step] of [...(scenario.preconditions || []), ...(scenario.steps || [])].entries()) {
    if (!step || typeof step !== 'object' || !SUPPORTED_ACTIONS.has(step.action)) {
      errors.push(`scenarios[${index}] 的第 ${stepIndex + 1} 个操作不受支持或缺少 action`);
    }
  }
  for (const [effectIndex, effect] of (scenario.effects || []).entries()) {
    if (!effect || typeof effect !== 'object' || !SUPPORTED_ASSERTIONS.has(effect.assertion)) {
      errors.push(`scenarios[${index}] 的第 ${effectIndex + 1} 个断言不受支持或缺少 assertion`);
    }
  }
  return errors;
}

function listContractFiles(root) {
  if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) return [];
  const files = [];
  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (entry.name.startsWith('.') || entry.name === 'node_modules') continue;
      const absolute = path.join(directory, entry.name);
      if (entry.isDirectory()) walk(absolute);
      else if (CONTRACT_PATTERN.test(entry.name)) files.push(absolute);
    }
  }
  walk(root);
  return files.sort();
}

function parseBusinessContracts(projectDir, contractDir = null) {
  const root = contractDir
    ? path.resolve(path.isAbsolute(contractDir) ? contractDir : path.join(projectDir, contractDir))
    : path.join(projectDir, 'src', 'test-contracts');
  const files = listContractFiles(root);
  const contracts = [];
  const errors = [];
  for (const file of files) {
    const parsed = parseContractFile(file);
    if (parsed.errors) {
      errors.push({ file, errors: parsed.errors });
      continue;
    }
    const route = parsed.value.route;
    const scenarios = parsed.value.scenarios;
    const contractErrors = [];
    if (typeof route !== 'string' || !route.trim()) contractErrors.push('route 必须是非空字符串');
    if (!Array.isArray(scenarios) || scenarios.length === 0) contractErrors.push('scenarios 必须是非空数组');
    const normalizedScenarios = Array.isArray(scenarios) ? scenarios.map((scenario, index) => ({
      ...scenario,
      route: scenario?.route || route,
      errors: validateScenario(scenario, index),
      sourceLine: lineAt(parsed.text, parsed.text.indexOf(String(scenario?.id || ''))),
    })) : [];
    if (contractErrors.length || normalizedScenarios.some(scenario => scenario.errors.length)) {
      errors.push({ file, errors: [...contractErrors, ...normalizedScenarios.flatMap(scenario => scenario.errors)] });
      continue;
    }
    contracts.push({
      file,
      route,
      sourceLine: parsed.sourceLine,
      scenarios: normalizedScenarios,
    });
  }
  return { root, files, contracts, errors };
}

module.exports = {
  SUPPORTED_ACTIONS,
  SUPPORTED_ASSERTIONS,
  parseBusinessContracts,
};
