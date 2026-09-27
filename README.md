# Ding Skill

一个只做声音提示的 Agent Skill：AI 需要用户决定、授权或补充信息前 `ding` 1 次；任务完整执行完毕后 `ding` 3 次。内置用户提供的 `ding.mp3`，不生成额外语音。

## 信号规则

| 场景 | 声音 | 触发时机 |
| --- | --- | --- |
| `confirm` | 1 次 | 即将向用户提问、要求选择、请求授权或补充信息前 |
| `done` | 3 次 | 任务全部完成，即将输出最终结果前 |

进度更新、工具调用、部分结果、报错中断不会触发 `done`。如果 AI 因需要决定而停下，则触发 1 次 `confirm`。同一轮中的多个相关问题只响 1 次。

## 仓库结构

```text
ding/
|-- SKILL.md
|-- agents/openai.yaml
|-- assets/ding.mp3
`-- scripts/ding.py
```

## 安装

这是一个符合通用 `SKILL.md` 目录结构的单个 Skill，可以安装到支持 Agent Skills 的 AI 工具中。

Codex：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R ding "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Claude Code 等使用 `.claude/skills` 的工具：

```bash
mkdir -p "$HOME/.claude/skills"
cp -R ding "$HOME/.claude/skills/"
```

Windows PowerShell：

```powershell
$skills = Join-Path $HOME ".codex\skills"
New-Item -ItemType Directory -Force $skills | Out-Null
Copy-Item -Recurse -Force .\ding $skills
```

如果某个 AI 工具只支持全局提示词、不支持自动发现 Skill，可把下面的规则加入它的全局系统提示词，并把路径替换为实际安装位置：

```text
Always follow the installed Ding skill at /absolute/path/to/ding/SKILL.md:
play one ding immediately before asking me to decide, approve, authorize, or clarify,
and play three dings immediately before the final response after a task is fully complete.
```

## 手动使用

macOS / Linux：

```bash
python3 ding/scripts/ding.py confirm
python3 ding/scripts/ding.py done
```

Windows：

```powershell
py -3 .\ding\scripts\ding.py confirm
py -3 .\ding\scripts\ding.py done
```

检查当前系统将使用哪个播放器：

```bash
python3 ding/scripts/ding.py done --dry-run
```

## 平台兼容

| 平台 | 播放方式 |
| --- | --- |
| macOS | `afplay` |
| Windows | PowerShell + `System.Windows.Media.MediaPlayer` |
| Linux | 按顺序尝试 `ffplay`、`mpg123`、`paplay`、`vlc`、`mpv`、`play` |
| 无音频设备或播放器 | 终端响铃回退 |

可以用环境变量替换默认音频：

```bash
DING_SOUND=/absolute/path/to/custom.mp3 python3 ding/scripts/ding.py confirm
```

也可以直接传参：

```bash
python3 ding/scripts/ding.py done --sound /absolute/path/to/custom.mp3
```

## 已知边界

原生工具审批弹窗、系统权限弹窗和远程无音频会话不一定允许模型在弹窗出现前执行命令。Ding Skill 覆盖 AI 能主动控制的对话决策点和最终完成点；在无播放器的服务器上会退化为终端响铃。

## 验证

```bash
python3 ding/scripts/ding.py confirm --dry-run
python3 ding/scripts/ding.py done --dry-run
```

如果本机安装了 Skill Creator，可以继续用它的 `quick_validate.py` 校验 `ding/`。
