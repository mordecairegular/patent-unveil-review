# Codex 试用安装说明

本目录就是一个完整的 Codex Skill。安装时请保留整个 `patent-unveil-review/` 文件夹，并确保安装后存在：

```text
<Codex skills 目录>/patent-unveil-review/SKILL.md
```

## Windows

如果拿到的是 `patent-unveil-review-codex-trial-*.zip`，在 PowerShell 中执行：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.codex\skills"
Expand-Archive -Path ".\patent-unveil-review-codex-trial-*.zip" -DestinationPath "$env:USERPROFILE\.codex\skills" -Force
```

解压后检查：

```powershell
Test-Path "$env:USERPROFILE\.codex\skills\patent-unveil-review\SKILL.md"
```

返回 `True` 即安装路径正确。

## macOS / Linux

```bash
mkdir -p ~/.codex/skills
unzip patent-unveil-review-codex-trial-*.zip -d ~/.codex/skills
test -f ~/.codex/skills/patent-unveil-review/SKILL.md && echo OK
```

## 启用与触发

安装后重启 Codex，或开启一个新线程。可用这些说法触发：

- `使用 patent-unveil-review 帮我做专利挖掘`
- `帮我根据这个项目生成技术交底书`
- `对这个方案做查新和授权可行性初筛`
- `在这份交底书上继续补材料/纠错`

## 可选依赖

仅让 Codex 阅读 prompts 并生成 Markdown 时，不强制安装依赖。

如需 Word/PPT 转 Markdown、Markdown 转 Word、公式/mermaid 图片渲染：

```bash
pip install -r requirements.txt
```

如需优先走国知局公布公告站查新工具：

```bash
pip install -r tools/requirements-cnipa.txt
python -m playwright install chromium
```

如需将 mermaid 图渲染成 PNG 并嵌入 Word，先安装 Node.js，再在 `tools/` 目录执行：

```bash
npm install
```

更完整的依赖说明见 `INSTALL.md` 和 `tools/README.md`。
