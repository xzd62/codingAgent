"""Skill 注册中心 — 发现、加载、管理可插拔能力包。"""

from pathlib import Path


class SkillInfo:
    def __init__(self, name: str, description: str, prompt: str, dir: Path,
                 enabled: bool = True):
        self.name = name
        self.description = description
        self.prompt = prompt
        self.dir = dir
        self.enabled = enabled


class SkillRegistry:
    def __init__(self, base_dir: str | Path = ""):
        if not base_dir:
            base_dir = Path(__file__).resolve().parent
        self._base_dir = Path(base_dir)
        self._skills: dict[str, SkillInfo] = {}
        self.scan()

    def scan(self):
        self._skills.clear()
        if not self._base_dir.is_dir():
            return
        for entry in sorted(self._base_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("__"):
                continue
            skill_md = entry / "skill.md"
            if not skill_md.exists():
                continue
            info = self._load_skill(entry, skill_md)
            if info:
                self._skills[info.name] = info

    def _load_skill(self, dir: Path, md_path: Path) -> SkillInfo | None:
        text = md_path.read_text(encoding="utf-8").strip()
        name = dir.name
        description = ""
        prompt = text

        # 解析 frontmatter (--- 包裹的 YAML)
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                front = text[3:end].strip()
                prompt = text[end + 3:].strip()
                for line in front.splitlines():
                    if line.startswith("name:"):
                        name = line[5:].strip().strip("\"'")
                    elif line.startswith("description:"):
                        description = line[12:].strip().strip("\"'")

        return SkillInfo(name=name, description=description,
                         prompt=prompt, dir=dir)

    def get_active_prompt(self) -> str:
        parts = []
        for skill in self._skills.values():
            if skill.enabled and skill.prompt:
                parts.append(f"### {skill.name}\n{skill.prompt}")
        if not parts:
            return ""
        return "## 已启用技能\n\n" + "\n\n".join(parts)

    def enable(self, name: str):
        if name in self._skills:
            self._skills[name].enabled = True

    def disable(self, name: str):
        if name in self._skills:
            self._skills[name].enabled = False

    def list_skills(self) -> list[dict]:
        return [
            {"name": s.name, "description": s.description, "enabled": s.enabled}
            for s in self._skills.values()
        ]

    def get_skill(self, name: str) -> SkillInfo | None:
        return self._skills.get(name)

    def delete_skill(self, name: str):
        skill = self._skills.get(name)
        if skill and skill.dir.is_dir():
            import shutil
            shutil.rmtree(skill.dir)
        self.scan()

    def create_skill(self, name: str, description: str = ""):
        dir = self._base_dir / name
        dir.mkdir(parents=True, exist_ok=True)
        front = f"---\nname: {name}\ndescription: {description}\n---\n"
        (dir / "skill.md").write_text(front, encoding="utf-8")
        self.scan()

    def save_skill(self, name: str, content: str):
        skill = self._skills.get(name)
        if skill and skill.dir.is_dir():
            (skill.dir / "skill.md").write_text(content.strip() + "\n", encoding="utf-8")
            self.scan()

    def reload(self):
        self.scan()


_global_registry: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry
