#!/bin/sh
# team-standards: portable Git policy. The installed copy is self-contained.
set -u
RULES_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -r "$RULES_DIR/rules.generated.sh" ]; then
    echo '团队规则配置缺失，请重新安装 team-standards Git 钩子。' >&2
    exit 1
fi
# C.UTF-8 is provided by Git for Windows, current macOS and Linux. Test actual
# character counting, rather than accepting a locale name libc silently ignores.
utf8_found=0
for rule_locale in C.UTF-8 en_US.UTF-8 UTF-8; do
    if [ "$(printf '中' | LC_ALL="$rule_locale" wc -m 2>/dev/null | tr -d ' ')" = 1 ]; then
        LC_ALL=$rule_locale
        export LC_ALL
        utf8_found=1
        break
    fi
done
if [ "$utf8_found" = 0 ]; then
    echo '团队规则需要 UTF-8 locale 以按字符校验中文，请使用 Git Bash 或启用 UTF-8 locale。' >&2
    exit 1
fi
. "$RULES_DIR/rules.generated.sh"

protected() {
    [ -n "$1" ] || return 1
    case "$1" in *'
'*) return 1 ;; esac
    printf '%s\n' "$RULE_PROTECTED_BRANCHES" | grep -F -x -q -e "$1"
}

branch() {
    protected "$1" && return 0
    case "$1" in *'
'*) ;; # grep is line-oriented; a branch is one complete string.
        *) if [ -n "$RULE_BRANCH_PATTERNS" ] && printf '%s\n' "$1" | grep -E -x -q -e "$RULE_BRANCH_PATTERNS"; then return 0; fi ;;
    esac
    echo "分支名不符合团队约定：$1。使用 feature|fix|refactor|docs|test|chore/<小写短横线描述> 或 release|hotfix/<版本>，例如 feature/PROJ-123-add-login。" >&2
    return 2
}

commit_msg() {
    if [ ! -r "$1" ]; then echo "无法读取提交信息文件：$1" >&2; return 1; fi
    # Match Python splitlines(), then skip blank lines and original '#'-comments.
    # A literal newline in sed's replacement is specified by POSIX.
    # Shell variables cannot retain NUL. SOH has identical whitespace/regex/length
    # behavior for the commit grammar, so translate it before reading lines.
    subject=$(tr '\000' '\001' < "$1" | sed "s/[$RULE_LINE_BREAKS]/\\
/g" | while IFS= read -r line || [ -n "$line" ]; do
        if [ "${line#\#}" != "$line" ]; then continue; fi
        line=$(printf '%s\n' "$line" | sed "s/^[$RULE_WHITESPACE]*//;s/[$RULE_WHITESPACE]*$//")
        if [ -n "$line" ]; then printf '%s' "$line"; break; fi
    done)
    if [ -z "$subject" ]; then
        echo '提交信息不能为空；示例：新增(认证): 支持用户登录。' >&2
        return 2
    fi
    case "$subject" in 'Merge '*|'Revert '*|'fixup! '*|'squash! '*|'合并:'*) return 0 ;; esac
    failed=0
    if [ -z "$RULE_COMMIT_TYPES" ] || ! printf '%s\n' "$subject" | grep -E -x -q \
        -e "($RULE_COMMIT_TYPES)(\([^)]+\))?!?:[$RULE_WHITESPACE]+[^$RULE_WHITESPACE].+"; then
        echo "提交信息应使用 <类型>(<范围>): <动作摘要>（范围可省略，摘要至少两个字符）；类型：${RULE_COMMIT_TYPES}。示例：新增(认证): 支持用户登录。" >&2
        failed=2
    fi
    length=$(printf '%s' "$subject" | wc -m | tr -d ' ')
    if [ "$length" -gt "$RULE_COMMIT_MAX_LENGTH" ]; then
        echo "提交摘要超过 $RULE_COMMIT_MAX_LENGTH 个字符：${length}；请缩短摘要，例如：修复(认证): 修复令牌刷新。" >&2
        failed=2
    fi
    return "$failed"
}

push_branch() {
    if protected "$1" && [ "${QUALITY_GATE_ALLOW_PROTECTED_PUSH:-}" != 1 ]; then
        echo "禁止直接推送受保护分支：$1，请通过合并请求进入；示例：git push origin feature/add-login。经授权的例外可设置 QUALITY_GATE_ALLOW_PROTECTED_PUSH=1。" >&2
        return 2
    fi
    branch "$1"
}

pre_push() {
    # Same splitlines()/split() behavior as Python, including CRLF and Unicode
    # separators. The function runs in the final pipeline process and returns its
    # status; no state is needed by the parent shell.
    tr '\000' '\001' | sed "s/[$RULE_LINE_BREAKS]/\\
/g;s/[$RULE_WHITESPACE]/ /g" | check_push_lines
}

check_push_lines() {
    failed=0
    while read -r local_ref local_sha remote_ref remote_sha extra || [ -n "$local_ref$local_sha$remote_ref$remote_sha$extra" ]; do
        [ -n "$remote_sha" ] && [ -z "$extra" ] || continue
        [ "$local_sha" = 0000000000000000000000000000000000000000 ] && continue
        case "$remote_ref" in refs/heads/*) push_branch "${remote_ref#refs/heads/}" || failed=$? ;; esac
    done
    return "$failed"
}

case "${1:-}" in
    branch) [ "$#" = 2 ] || exit 1; branch "$2" ;;
    commit-msg) [ "$#" = 2 ] || exit 1; commit_msg "$2" ;;
    pre-push) pre_push ;;
    agent-command)
        if ! command -v perl >/dev/null 2>&1; then
            echo '警告：未找到 Perl，跳过 Agent 命令预检；请启用项目 Git 钩子兜底。' >&2
            exit 0
        fi
        exec perl "$RULES_DIR/agent-command.pl" "$RULES_DIR/git-rules.sh"
        ;;
    *) echo '用法：git-rules.sh branch <分支名> | commit-msg <消息文件> | pre-push | agent-command' >&2; exit 1 ;;
esac
