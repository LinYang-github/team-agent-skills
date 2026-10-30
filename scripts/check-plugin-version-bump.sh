#!/usr/bin/env sh
# 发布约束：改了项目 Git 钩子会复制的文件（hooks/lib/、quality-gates.json），
# 就必须升插件版本号。各项目的 SessionStart 只按版本号"只升不降"同步钩子，
# 不升版本号，已启用钩子的项目拿不到新规则。
# 比较基准默认 origin/develop，可用 PLUGIN_VERSION_BASE 覆盖。
set -eu

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
base_ref=${PLUGIN_VERSION_BASE:-origin/develop}

if ! git rev-parse --verify --quiet "$base_ref^{commit}" >/dev/null; then
    echo "WARNING: 找不到比较基准 ${base_ref}，跳过插件版本号检查。" >&2
    exit 0
fi
base=$(git merge-base HEAD "$base_ref")

changed=$(git diff --name-only "$base" HEAD -- hooks/lib quality-gates.json)
[ -n "$changed" ] || exit 0

version_of() {
    sed -n 's/^[[:space:]]*"version": "\([0-9][0-9.]*\)".*/\1/p'
}
old=$(git show "$base:package.json" 2>/dev/null | version_of || true)
new=$(version_of < package.json)

if [ -n "$old" ] && [ "$old" = "$new" ]; then
    echo "[ERROR] 以下文件会被复制进各项目的 Git 钩子，但插件版本号仍是 ${new}：" >&2
    printf '  %s\n' $changed >&2
    echo "请同步升级 package.json、.codex-plugin/plugin.json、.claude-plugin/plugin.json、两个 marketplace.json 中的 version。" >&2
    exit 1
fi
echo "[PASS] 插件版本号检查（${old} -> ${new}）"
