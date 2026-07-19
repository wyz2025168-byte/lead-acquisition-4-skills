# 安装与更新

## GitHub 一句话安装

公开仓库：

```bash
npx -y skills add wyz2025168-byte/lead-acquisition-4-skills -g --all
```

这条命令同时用于首次安装和后续更新。

## 本地发行候选安装

```bash
npx -y skills add "/absolute/path/to/lead-acquisition-4-skills" -g --all
```

## 只装一个 Skill

```bash
npx -y skills add wyz2025168-byte/lead-acquisition-4-skills --skill jw-positioning -g
```

## 安装后入口

先说：

```text
使用 $jw，帮我选择现在该测试哪个能力。
```

或直接使用 `$jw-positioning`、`$jw-lock`、`$jw-circle`、`$jw-convert`、`$jw-grow`、`$jw-production`、`$jw-orchestrator`。

如果 Agent 在安装后没有立即刷新 Skill 列表，新建任务或重启宿主。
