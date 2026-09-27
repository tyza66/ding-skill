# Ding Skill

一个只做声音提示的 Agent Skill：AI 需要用户决定、授权或补充信息前 `ding` 1 次；任务完整执行完毕后 `ding` 3 次。内置用户提供的 `ding.mp3` 及其 WAV 兼容副本，不生成额外语音。

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
|-- assets/
|   |-- ding.mp3
|   `-- ding.wav
`-- scripts/
    |-- ding          # macOS / Linux / WSL / Git Bash / MSYS2 / Cygwin
    |-- ding.cmd      # Windows CMD
    |-- ding.ps1      # Windows PowerShell
    `-- ding.py       # Python 通用回退
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

macOS、Linux、WSL、Git Bash、MSYS2、Cygwin：

```bash
sh ding/scripts/ding confirm
sh ding/scripts/ding done
```

Windows CMD：

```bat
ding\scripts\ding.cmd confirm
ding\scripts\ding.cmd done
```

Windows PowerShell：

```powershell
& .\ding\scripts\ding.ps1 -Signal confirm
& .\ding\scripts\ding.ps1 -Signal done
```

Python 通用回退：

```bash
python3 ding/scripts/ding.py confirm
python3 ding/scripts/ding.py done
```

```powershell
py -3 .\ding\scripts\ding.py confirm
py -3 .\ding\scripts\ding.py done
```

## 播放后端

| 平台或环境 | 回退顺序 |
| --- | --- |
| macOS | `afplay` -> `ffplay` -> `mpg123` -> 终端响铃 |
| Windows 10/11 | PowerShell MediaPlayer -> WAV SoundPlayer -> `ffplay` -> `mpg123` -> `mpg321` -> `mpv` -> `mplayer` -> VLC -> 控制台蜂鸣 |
| Linux 桌面 | `pw-play` -> `paplay` -> `ffplay` -> `mpg123` -> `mpg321` -> `mpv` -> `mplayer` -> VLC -> GStreamer -> SoX -> ALSA WAV -> 终端响铃 |
| WSL | Linux 播放器 -> Windows 主机 PowerShell 桥接 -> 终端响铃 |
| Git Bash / MSYS2 / Cygwin | POSIX 播放器 -> Windows 主机 PowerShell 桥接 -> 终端响铃 |
| SSH / 容器 / 无桌面环境 | 有可用后端时播放，否则终端响铃 |

Windows 播放器脚本会优先播放 MP3；如果系统编解码器不可用，会自动使用内置 WAV 和 `System.Media.SoundPlayer`。Python 脚本同样会启用 Windows 主机桥接。

## 检查与自定义音频

检查当前系统识别的播放后端：

```bash
sh ding/scripts/ding done --dry-run
python3 ding/scripts/ding.py done --dry-run
```

```powershell
& .\ding\scripts\ding.ps1 -Signal done -DryRun
```

替换默认音频：

```bash
DING_SOUND=/absolute/path/to/custom.mp3 sh ding/scripts/ding confirm
```

```powershell
$env:DING_SOUND = "C:\absolute\path\to\custom.wav"
& .\ding\scripts\ding.ps1 -Signal confirm
```

也可以使用参数：

```bash
sh ding/scripts/ding done --sound /absolute/path/to/custom.mp3
python3 ding/scripts/ding.py done --sound /absolute/path/to/custom.mp3
```

```powershell
& .\ding\scripts\ding.ps1 -Signal done -Sound "C:\absolute\path\to\custom.wav"
```

## AI 工具兼容

- 支持标准 `SKILL.md` 发现机制的 AI 工具可以直接安装整个 `ding/` 目录。
- 支持本地命令执行的工具可以调用原生启动器，不需要安装 Python 或第三方 Python 包。
- 只支持系统提示词的工具可以引用 `SKILL.md` 或加入上面的全局提示词规则。
- 沙箱禁止启动进程、访问音频设备或执行脚本时，任何声音方案都无法保证播放；脚本会尽可能回退到终端响铃。
- 云端或远程 AI 执行器的声音会发生在执行主机上，不可能无条件传回用户本地电脑。要在本地听到声音，Skill 必须运行在用户本机客户端。

## 已知边界

原生工具审批弹窗、系统权限弹窗和远程无音频会话不一定允许模型在弹窗出现前执行命令。Ding Skill 覆盖 AI 能主动控制的对话决策点和最终完成点。终端响铃也可能被终端、SSH 客户端、tmux 或系统设置静音。

## 验证

```bash
sh -n ding/scripts/ding
python3 ding/scripts/ding.py confirm --dry-run
python3 ding/scripts/ding.py done --dry-run
```
