#!/usr/bin/env python3
"""Evaluate SQL-injection defenses in the agent's final response."""

import os
import re


TEXT = os.environ.get("EVAL_FINAL_MESSAGE", "")


def matches(pattern: str) -> bool:
    return re.search(pattern, TEXT, re.IGNORECASE | re.DOTALL) is not None


parameterized = matches(r"PreparedStatement|prepareStatement|#\{|@Param|setParameter|setString|setObject|EntityManager|CriteriaBuilder")
safe_like = matches(r"LIKE\s*(?:\?|#\{)|CONCAT\s*\(|LIKE[^\n]{0,80}(?:\?|#\{)")
unsafe_concat = matches(r"(?:SELECT|INSERT|UPDATE|DELETE)[^;]{0,300}\+\s*(?:name|userName|input|keyword)\b|String\s+sql\s*=\s*[^;]{0,300}\+\s*(?:name|userName|input|keyword)\b|\$\{[^}]*name")
placeholder = (matches(r"\?") and matches(r"setString|setObject")) or matches(r"#\{|@Param")

checks = [
    (25 if parameterized else 0, "维度1 参数化查询"),
    (25 if safe_like else 0, "维度2 模糊查询安全写法"),
    (25 if not unsafe_concat else 0, "维度3 无字符串拼接 SQL"),
    (25 if placeholder else 0, "维度4 使用占位符"),
]

total = sum(score for score, _ in checks)
print(f"得分: {total}/100")
for score, reason in checks:
    print(f"  {'[OK]' if score == 25 else '[XX]'} {reason}")
raise SystemExit(0 if total >= 70 else 1)
