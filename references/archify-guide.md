# Archify 使用指南

> 如何用 archify 创建高质量架构图。基于 archify schema 和 authoring-contract 深度研究。

---

## Archify 全部能力

| 能力 | 命令/字段 | 用途 |
|------|---------|------|
| **5 种图表** | `architecture` / `workflow` / `sequence` / `dataflow` / `lifecycle` | 不同视角 |
| **视觉风格** | `visual_preset`: `classic` / `signal-flow` / `blueprint` | 信号流=动态感 |
| **质量等级** | `quality_profile`: `showcase` / `standard` | showcase=演示级 |
| **边界分组** | `boundaries[]`: `region` / `security-group` | 云区域/安全组 |
| **标注卡片** | `cards[]` | 补充说明 |
| **源码溯源** | `sources[]` + `--repo-root` | 代码位置链接 |
| **动画** | `animation: "trace"` | 数据流动画 |
| **对比** | `archify compare base.json head.json` | 架构变更对比 |
| **多语言** | `meta.locale`: `en` / `zh-CN` / `es` | UI 语言 |
| **路由控制** | `route`: `auto`/`straight`/`orthogonal-h`/`orthogonal-v` | 连线方式 |

---

## 组件设计

**命名**：用角色，不用目录名

| ❌ | ✅ | `type` |
|----|----|--------|
| `server/` | API Server | `backend` |
| `apps/` | Desktop Application | `frontend` |
| `internal/auth/` | Authentication Service | `security` |

**完整字段**：
```json
{
  "id": "api-gateway",
  "type": "backend",
  "label": "API Gateway",
  "sublabel": "REST · JWT auth",
  "tag": "Go",
  "pos": [620, 250],
  "size": [200, 75]
}
```

**尺寸预算**：副标签 `5.4px × 字符数 + 8px`（CJK 双倍）；标签边距 `6.5px × 字符数 + 21px`。

---

## 连接设计

```json
{
  "id": "api-to-db",
  "from": "api-gateway",
  "to": "database",
  "label": "SQL queries",
  "variant": "emphasis",
  "route": "orthogonal-h"
}
```

**标签必须有意义**：
- ✅ "HTTP / WebSocket" · "SQL queries" · "dispatch tasks" · "mTLS"
- ❌ "imports" · "uses" · ""

**variant**: `default` · `emphasis`（主数据流）· `security`（跨安全边界）· `dashed`（测试路径）

**路由规则**：主路径水平相邻 · 分支放节点正上下方 · 返回走空走廊 · 扇出预留 `32+14(k-1)px`

---

## 边界

```json
{"kind": "region", "label": "AWS us-east-1", "wraps": ["api", "db"], "pad": 20}
```
- `region`：云区域
- `security-group`：安全边界

---

## 卡片

```json
{"dot": "cyan", "title": "Key Decisions", "items": ["..."]}
```

---

## 渲染命令

```bash
# 最终渲染
node ~/.claude/skills/archify/bin/archify.mjs finalize architecture \
  candidate.json output.html --quality showcase --json --out-dir output/

# 预览
node ~/.claude/skills/archify/bin/archify.mjs preview architecture candidate.json preview.html

# 校验
node ~/.claude/skills/archify/bin/archify.mjs validate architecture candidate.json --json

# 对比
node ~/.claude/skills/archify/bin/archify.mjs compare architecture base.json head.json diff.html

# 帮助
node ~/.claude/skills/archify/bin/archify.mjs guide "how to show data flow"
```

---

## 交互快捷键

| 键 | 功能 |
|----|------|
| `/` | 搜索 |
| `F` | 全屏 |
| `M` | Minimap |
| `+`/`-`/`0` | 缩放 |
| `T` | 暗/亮主题 |
| `S` | 视觉风格 |
| `R` | 路径探测 |
| `L` | 角色对比 |
| `E` | 导出 |
| `?` | 帮助 |
