"""技能加载工具 — 按需获取技能指引。"""

from tool.registry import registry
from skill.registry import get_registry

LOAD_SKILL_SCHEMA = {
    "name": "load_skill",
    "description": "加载某个技能的详细使用指引。技能是预定义的能力包，包含特定任务的指令和用法。调用后返回该技能的完整说明。",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "技能名称，如 web_search、codegraph 等",
            },
        },
        "required": ["name"],
    },
}


# ============================================================
#  ★ 你来实现这部分 ★
#  从 SkillRegistry 查找并返回技能指引
# ============================================================
def load_skill_handler(args):
    """根据技能名称加载指引。

    你需要完成：
      1. 提取 name 参数
      2. 从 skill.registry.get_registry() 获取 registry
      3. 用 registry.get_skill(name) 查找
      4. 找到 → 返回 {"success": True, "content": skill.prompt}
      5. 没找到 → 返回 {"success": False, "error": "技能 'xxx' 不存在"}
    """
    # ── 你的代码写在这里 ──
    name = args["name"]

    registry = get_registry()

    skill = registry.get_skill(name=name)
    if skill is None:
        return {"success": False, "error": f"技能 '{name}' 不存在"}
    else:
        return {"success": True, "content": skill.prompt}


registry.register(
    name="load_skill",
    handler=load_skill_handler,
    schema=LOAD_SKILL_SCHEMA,
)
