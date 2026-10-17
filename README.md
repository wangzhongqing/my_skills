# my_skills

个人维护的 AI Agent skills 集合。

每个 skill 是一个独立目录，遵循 `SKILL.md` 约定，可直接复制到 Agent 的 skills 目录使用。

## 包含的 skills

| Skill | 说明 | 许可证 |
|---|---|---|
| [eli5-plus-plus](./eli5-plus-plus/) | 把复杂主题解释成自包含、经过三层机械校验的 HTML 图解页 | MIT |

## 安装

```bash
git clone https://github.com/<你的用户名>/my_skills.git
cp -R my_skills/<skill-name> ~/.agents/skills/
```

不同 Agent 的 skills 目录位置不同，常见：

- `~/.agents/skills/` — 通用
- `~/.claude/skills/` — Claude Code

安装后重启或开新任务，让 Agent 重新发现 skills。

## 目录约定

```
my_skills/
├── README.md              # 本文件
├── .gitignore
└── <skill-name>/          # 每个 skill 一个目录
    ├── SKILL.md           # 必需：主指令（含 YAML frontmatter）
    ├── README.md          # 可选：面向人的说明
    ├── LICENSE            # 建议：独立许可证
    ├── agents/            # 可选：客户端元数据
    ├── assets/            # 可选：模板、图片等产出用素材
    ├── evals/             # 可选：行为测试用例
    ├── references/        # 可选：按需加载的参考文档
    └── scripts/           # 可选：可执行脚本
```

## 许可证

各 skill 的许可证见其各自目录下的 `LICENSE` 文件。
