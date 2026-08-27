#!/usr/bin/env node

const path = require('node:path');
const { parseBusinessContracts } = require('./business-contracts');

function fail(message) {
  console.error(message);
  process.exit(1);
}

function parseArgs(argv) {
  const args = { projectDir: null, contractDir: null };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--project-dir') args.projectDir = argv[++index];
    else if (argv[index] === '--contract-dir') args.contractDir = argv[++index];
    else fail(`未知参数: ${argv[index]}`);
  }
  if (!args.projectDir) fail('请使用 --project-dir 指定前端工程。');
  return args;
}

const args = parseArgs(process.argv.slice(2));
const projectDir = path.resolve(args.projectDir);
const result = parseBusinessContracts(projectDir, args.contractDir);
console.log(JSON.stringify({
  root: result.root,
  files: result.files,
  contracts: result.contracts.map(contract => ({
    file: contract.file,
    route: contract.route,
    scenarios: contract.scenarios.map(scenario => scenario.id),
  })),
  errors: result.errors,
}, null, 2));
if (result.errors.length) process.exit(1);
