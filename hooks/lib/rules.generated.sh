# 由 scripts/generate-git-rules.py 生成，勿手改。
# 规则来源：quality-gates.json；运行生成脚本后提交此文件。
RULE_BRANCH_PATTERNS='^(feature|fix|refactor|docs|test|chore)/([A-Za-z][A-Za-z0-9]*-[0-9]+-)?[a-z0-9]+(-[a-z0-9]+)*$
^(release|hotfix)/[A-Za-z0-9][A-Za-z0-9._-]*$'
RULE_COMMIT_TYPES='新增|修复|重构|优化|文档|测试|构建|工具|规范|回滚'
RULE_COMMIT_MAX_LENGTH=72
RULE_PROTECTED_BRANCHES='main
develop'
RULE_WHITESPACE=$(printf '\011\013\014\015\034\035\036\037\040\302\205\302\240\341\232\200\342\200\200\342\200\201\342\200\202\342\200\203\342\200\204\342\200\205\342\200\206\342\200\207\342\200\210\342\200\211\342\200\212\342\200\250\342\200\251\342\200\257\342\201\237\343\200\200')
RULE_LINE_BREAKS=$(printf '\015\013\014\034\035\036\302\205\342\200\250\342\200\251')
