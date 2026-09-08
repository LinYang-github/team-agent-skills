#!/usr/bin/env python3
"""Evaluate null-safety guidance in the agent's final response."""

import os
import re


TEXT = os.environ.get("EVAL_FINAL_MESSAGE", "")


def matches(pattern: str) -> bool:
    return re.search(pattern, TEXT, re.IGNORECASE | re.DOTALL) is not None


checks = [
    (
        25 if matches(r"Objects\.requireNonNull|StringUtils\.(?:isEmpty|isBlank)|Assert\.(?:notNull|hasText)|Validate\.notNull|Preconditions\.checkNotNull|@(?:NonNull|NotNull|NotBlank)") else 0,
        "维度1 具名校验 API",
    ),
    (
        25 if not matches(r"return\s+null\s*;") or matches(r"@Nullable|null[^\n]{0,40}(?:contract|契约|Javadoc)|(?:may return|可能返回|允许返回|可以返回)\s*null") else 0,
        "维度2 返回值 null 契约",
    ),
    (
        25 if matches(r"Collections\.(?:emptyList|emptySet|emptyMap)|new\s+(?:ArrayList|HashSet|HashMap|CopyOnWriteArrayList)|Stream\.empty") else 0,
        "维度3 集合返回空集合",
    ),
    (
        25 if not matches(r"\.printStackTrace\s*\(|catch\s*\([^)]*\)\s*\{\s*\}") else 0,
        "维度4 未吞异常",
    ),
]

total = sum(score for score, _ in checks)
print(f"得分: {total}/100")
for score, reason in checks:
    print(f"  {'[OK]' if score == 25 else '[XX]'} {reason}")
raise SystemExit(0 if total >= 70 else 1)
