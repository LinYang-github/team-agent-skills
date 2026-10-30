#!/bin/sh
# Install standalone hooks; never change core.hooksPath or overwrite another tool.
set -eu
LIB_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
uninstall=0
if [ "${1:-}" = --uninstall ]; then uninstall=1; shift; fi
if [ "$#" != 1 ]; then
    echo '用法：sh hooks/lib/install-git-hooks.sh [--uninstall] <仓库目录>' >&2
    exit 1
fi
repo=$(CDPATH= cd -- "$1" && pwd)
git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 || {
    echo '目标目录不是 Git 仓库。' >&2; exit 1;
}
if git -C "$repo" config --get core.hooksPath >/dev/null 2>&1; then
    echo '仓库已设置 core.hooksPath（可能使用 husky 或本仓库 Python 门禁），不覆盖；请保留现有门禁并由维护者手动集成团队规则。' >&2
    exit 1
fi
hooks=$(cd "$repo" && git rev-parse --git-path hooks)
case "$hooks" in /*|[A-Za-z]:/*) ;; *) hooks=$repo/$hooks ;; esac
owner='# team-standards managed hook v1'
for name in commit-msg pre-push; do
    path=$hooks/$name
    if [ -L "$path" ] || { [ -e "$path" ] && { [ ! -f "$path" ] || ! grep -F -x -q -e "$owner" "$path"; }; }; then
        echo "已有非 team-standards 生成的 $name 钩子，不覆盖；请由维护者手动集成。" >&2
        exit 1
    fi
done
data=$hooks/team-standards
if [ -L "$data" ] || [ -L "$data/.managed" ] || { [ -e "$data" ] && { [ ! -f "$data/.managed" ] || [ "$(cat "$data/.managed")" != team-standards ]; }; }; then
    echo 'Git hooks/team-standards 目录已被其他内容占用，不覆盖。' >&2
    exit 1
fi
if [ -L "$hooks/.team-standards-version" ]; then
    echo 'Git 钩子版本标记不能是符号链接，请由维护者检查。' >&2; exit 1
fi
if [ "$uninstall" = 1 ]; then
    for name in commit-msg pre-push; do
        [ ! -f "$hooks/$name" ] || rm "$hooks/$name"
    done
    if [ -d "$data" ]; then
        rm -f "$data/git-rules.sh" "$data/rules.generated.sh" "$data/agent-command.pl" "$data/.managed"
        rmdir "$data" 2>/dev/null || : # retain any user-added files
    fi
    rm -f "$hooks/.team-standards-version"
    echo '已卸载 team-standards 项目 Git 钩子。'
    exit 0
fi
version=$(sed -n 's/^[[:space:]]*"version": "\([0-9][0-9.]*\)".*/\1/p' "$LIB_DIR/../../package.json")
if [ -z "$version" ]; then echo '插件版本配置缺失，请重新安装插件。' >&2; exit 1; fi
mkdir -p "$hooks"
stage=$(mktemp -d "$hooks/.team-standards-stage.XXXXXX")
trap 'rm -rf "$stage"' EXIT HUP INT TERM
for name in git-rules.sh rules.generated.sh agent-command.pl; do
    cp "$LIB_DIR/$name" "$stage/$name"
done
for name in commit-msg pre-push; do
    cat > "$stage/$name" <<EOF
#!/bin/sh
$owner
HOOK_DIR=\$(CDPATH= cd -- "\$(dirname -- "\$0")" && pwd)
exec sh "\$HOOK_DIR/team-standards/git-rules.sh" $name "\$@"
EOF
    chmod +x "$stage/$name"
done
mkdir -p "$data"
printf '%s\n' team-standards > "$data/.managed"
for name in git-rules.sh rules.generated.sh agent-command.pl; do mv "$stage/$name" "$data/$name"; done
for name in commit-msg pre-push; do mv "$stage/$name" "$hooks/$name"; done
printf '%s\n' "$version" > "$stage/version"
mv "$stage/version" "$hooks/.team-standards-version"
echo "已启用 team-standards $version 项目 Git 钩子。"
