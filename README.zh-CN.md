<div align="right"><a href="./README.md">English</a> | <strong>中文</strong></div>

# adaptive-workloop

**面向非简单 AI 编码工作的风险流程路由器。** 它判断任务需要多少规划、确定性验证、独立审查、持久状态和协作，再把具体阶段技术交给专项 Skill。

> 流程是成本：失败代价高时才投入；裸模型已经稳定完成的地方就删除流程。

当前状态：**0.2.2 candidate**。确定性包校验、完整性、安全、CI 和 Codex standalone 回归已经实现；在晋升 stable 前，仍需完成真实模型的 bare / previous / candidate 行为矩阵。

## 何时触发

用于存在多步骤、歧义、高风险边界、弱验证、独立审查、多会话延续或模型/Host 能力差异的工程任务；也用于恢复已有 `.workloop` episode，以及用户明确询问任务该走多重流程时。

普通单步编辑、孤立小 Bug、独立 Review、纯问答和纯文字工作继续走 Host 的默认快速路径。

## 四条路线

| 路线 | 适用条件 |
|---|---|
| **Direct** | 用户明确调用后发现任务极小、可逆，diff 本身足以证明。 |
| **Verified** | 有或可以低成本增加确定性校验，且没有高风险信号。 |
| **Reviewed** | 高风险、完成标准主观，或确定性验证薄弱/缺失。 |
| **Distributed** | 必须跨会话恢复，或独立分片通过 Multi-Agent Cost gate。 |

Workloop 拥有路线、Gate、预算、状态与编排权；被委托的 Skill 只拥有当前阶段的技术方法。Host 原生编排与 Workloop Route 4 只能选择一个 owner，避免递归 Agent 树。

## 安全与证据

路线 2–4 创建 episode：不可变 manifest、可变 state、append-only events、人类可读 contract，以及结构化 `checks.json`。

Check 使用 argv 数组，不接受 Shell 字符串：

```json
{
  "schema": "workloop-checks/1",
  "checks": [{
    "id": "tests",
    "description": "目标测试通过",
    "argv": ["python3", "-m", "pytest", "tests/test_feature.py"],
    "cwd": ".",
    "timeout_seconds": 120,
    "expected_exit": 0,
    "output_must_match": ["[1-9][0-9]* passed"],
    "risk": "workspace-local"
  }],
  "manual": []
}
```

验证器不经过 Shell，限制 cwd 不得逃逸仓库，强制 timeout，输出成功命令的 stdout/stderr，并保存 grading artifact。仓库快照摘要基于文件内容，而不只是 dirty path 标签。Append-only events 是持久 write-ahead record；下一次状态迁移前会先校验事件链，并从中修复陈旧的 `state.json` cache。Host 的 sandbox、权限、网络策略和用户批准始终权威；验证器不是权限绕过通道。

## 安装

Codex 默认只需安装 `adaptive-workloop`。Waza、Superpowers、gstack 和 mattpocock/skills 是设计来源及可选专项能力，不是运行依赖。缺少专项 Skill 时使用 Host 原生 fallback，运行中不会隐式安装。

```bash
npx skills add ./adaptive-workloop

# 或复制到 Codex Skill 目录
cp -r adaptive-workloop ~/.codex/skills/
```

Codex UI 元数据位于 `agents/openai.yaml`。确定性脚本需要 macOS/Linux + Python 3.10+。

## 命令

```bash
# 仓库事实，以及可选的 Host 能力清单
scripts/probe-capabilities . [--capabilities capabilities.json]

# 路线 2–4；Distributed 默认创建可追踪持久状态
scripts/create-episode --task "添加 CSV 导入器" --route verified --model "unknown"

# contract.md 与 checks.json 填好后开始执行
scripts/episode-state .workloop/local/<episode-id> --status in_progress --kind work.started

# 严格结构化验证
scripts/verify-contract .workloop/local/<episode-id>

# 追加生命周期事件并更新可变状态
scripts/episode-state .workloop/local/<episode-id> \
  --status verified --kind verification.passed --evidence evidence/grading.json

# 扫描 Distributed episode 的 Git 可见面，不输出命中的敏感值
scripts/check-episode .workloop/tracked/<episode-id>

# 包与 Eval 校验
scripts/check
scripts/run-evals --validate

# 在没有可选专项 Skill 时验证四条路线
scripts/run-evals --suite standalone \
  --host-profile codex-standalone \
  --adapter <provider-adapter> \
  --output evals/runs/codex-standalone
```

## 状态存储

- Verified/Reviewed：`.workloop/local/` 是被忽略的本地运行状态。
- Distributed：`.workloop/tracked/` 的脱敏 manifest/state/events/contract/checks/progress/handoff 可进入 Git；runtime、能力快照与 evidence 保持忽略。
- `.workloop/proposals/` 不被忽略，使改进提案能进入人工评审。

如果整个 workspace 本身会销毁，必须配置外部 issue/task store，不能仅凭本地文件声称“可持久恢复”。

## 目录

```text
adaptive-workloop/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── probe-capabilities
│   ├── create-episode
│   ├── verify-contract
│   ├── episode-state
│   ├── check-episode
│   ├── run-evals
│   └── check
├── references/
├── assets/
│   ├── contract.md
│   ├── checks.json
│   ├── progress.md
│   └── handoff.md
├── evals/
│   ├── trigger-cases.json
│   ├── behavior-cases.json
│   ├── regression-cases.json
│   ├── standalone-cases.json
│   ├── profiles/codex-standalone.json
│   └── adapter-contract.md
└── tests/
```

## 评测

`scripts/run-evals` 校验全部公开套件，也能运行 provider-neutral adapter。发送给 adapter 的 request 不包含 expected label。Trigger 和 standalone conformance 由 runner 精确评分。Standalone 产物必须真实存在于 runner 所有的 `artifact_root` 内，并与 adapter 声明的 SHA-256 一致；仅返回路径声明会失败。Behavior 与 Regression 在独立 grader 检查输出、状态、产物和 trace 前保持 `review_required`，因此默认以状态码 3 退出；只有明确使用 `--allow-review-required` 收集待审结果时才返回成功。

Standalone suite 固定 `installed_skills=[]`、`subagents=false`、`browser=false`，覆盖四条路线，拒绝 trace 中调用任何不可用 Skill，并要求缺少独立 verifier 的高风险任务停在 `needs_human`。它证明 fallback wiring，不代表真实模型质量。

对同一 fixture 分别运行 `bare`、`previous`、`candidate`，固定模型、Host、effort、tools、repository snapshot 与 runtime envelope。进行重复 trial，比较 verified success、pass^k、人工介入、延迟、成本、回滚和事故，而不只比较路线文案。

仓库内用例属于公开回归，不是真正 held-out 证据。Stable 晋升需要 proposer 无法访问的私有 held-out suite。

GitHub CI 在 Linux 的 Python 3.10、3.12、3.14 和 macOS 的 Python 3.12 上执行确定性 gate 与固定版本 Ruff；运行时包本身仍然只依赖标准库。

## 模型策略

路由不依赖模型品牌。未知模型使用同样路线和 authority，只收紧验证节奏。只有实测的 model-plus-host 差异才能加入简短、会过期的 counter-instruction；active ledger 出厂为空。干净验证 streak 只能扩大当前 episode 的步长，不能生成永久模型 profile。

## 谱系

本设计组合了 harness-engineering 的实证控制、Waza 的克制、Superpowers 的独立验证、gstack 的 runtime discipline，以及 mattpocock/skills 的可组合性，但不复制其完整工作流，也不依赖这些包。

## License

MIT
