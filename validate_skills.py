#!/usr/bin/env python3
"""Validate the skill folders in this repo.

Two skills that tell other people how to keep a test suite honest should not
themselves ship a broken reference link or a frontmatter name that stopped
matching its folder. This is the smallest check that would notice.

It checks, per skill folder:
  - SKILL.md exists and opens with a --- frontmatter block
  - frontmatter `name` matches the folder name, which is how a skill is invoked
  - frontmatter `description` exists and fits the 1024-character limit
  - every references/*.md path mentioned in SKILL.md actually exists
  - every file in references/ is mentioned by SKILL.md, so nothing rots unread

Run it with `python validate_skills.py`. No dependencies: the frontmatter here is
two keys, and a YAML library for two keys is a dependency for nothing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DESCRIPTION_LIMIT = 1024


def frontmatter(text: str) -> dict[str, str] | None:
    """The opening --- block, with folded (`>-`) values joined into one line."""
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not match:
        return None

    fields: dict[str, str] = {}
    key: str | None = None
    for line in match.group(1).splitlines():
        top = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if top:
            key = top.group(1)
            value = top.group(2).strip()
            fields[key] = "" if value in (">-", ">", "|", "|-") else value
        elif key and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def check(skill_dir: Path) -> list[str]:
    problems: list[str] = []
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        return [f"{name}: no SKILL.md"]

    text = skill_md.read_text(encoding="utf-8")
    fields = frontmatter(text)
    if fields is None:
        return [f"{name}/SKILL.md: no --- frontmatter block at the top"]

    if fields.get("name") != name:
        problems.append(
            f"{name}/SKILL.md: frontmatter name is {fields.get('name')!r}, "
            f"but the folder is {name!r}; a skill is invoked by the frontmatter name"
        )

    description = fields.get("description", "")
    if not description:
        problems.append(f"{name}/SKILL.md: frontmatter has no description")
    elif len(description) > DESCRIPTION_LIMIT:
        problems.append(
            f"{name}/SKILL.md: description is {len(description)} characters, "
            f"over the {DESCRIPTION_LIMIT} limit"
        )

    mentioned = set(re.findall(r"references/([A-Za-z0-9._-]+\.md)", text))
    for filename in sorted(mentioned):
        if not (skill_dir / "references" / filename).is_file():
            problems.append(f"{name}/SKILL.md: links references/{filename}, which does not exist")

    references = skill_dir / "references"
    on_disk = {p.name for p in references.glob("*.md")} if references.is_dir() else set()
    for filename in sorted(on_disk - mentioned):
        problems.append(
            f"{name}/references/{filename}: on disk but never mentioned in SKILL.md, "
            f"so nothing would load it"
        )

    return problems


def main() -> int:
    skills = sorted(p.parent for p in ROOT.glob("*/SKILL.md"))
    if not skills:
        print("No skill folders found (expected at least one */SKILL.md).")
        return 1

    problems = [problem for skill in skills for problem in check(skill)]
    for problem in problems:
        print(f"FAIL {problem}")

    if problems:
        print(f"\n{len(problems)} problem(s) across {len(skills)} skill(s).")
        return 1

    print(f"OK {len(skills)} skill(s) valid: {', '.join(s.name for s in skills)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
