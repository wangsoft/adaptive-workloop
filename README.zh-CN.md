<div align="right"><a href="./README.md">English</a> | <strong>中文</strong></div>

# adaptive-workloop

**面向非简单工作的「按风险路由 + 证据门禁」编排器。** 四个属性构成差异化：流程**与任务风险成比例**（改错别字和生产库迁移不该走同一套仪式）、完成**由可证伪且可审计的证据证明而非声称**（能确定性校验时运行，主观判断时具名确认）、路由**对模型品牌无关**（未知模型是受支持的输入，不是失败），以及**已证明的能力永不扩大权限**。这些属性搭在一个 Goal→Plan→Do→Check→Act 循环、四条路线之上；专项 Skill 继续负责阶段内技术。

> 流程是成本：失败代价高时才投入；裸模型已经稳定完成的地方就删除流程。

当前状态：**0.7.0 candidate**。Goal/Plan Gate、领域验证 Profile、类型化分派契约、摘要绑定关闭、只生成候选的学习机制、受控 Skill 改进、可选 Trace 证据挖掘、确定性打包及 Codex/Claude 兼容门禁已经实现；晋升 stable 前仍需独立架构审查，以及真实模型的 proposer-blind held-out 与 audit-held-out 证据。

## 何时触发

它可作为非简单工程、研究、写作/设计、个人规划和运营工作的默认外层流程，尤其适用于多步骤、歧义、高风险边界、弱验证、独立审查、多会话延续或模型/Host 能力差异；也用于恢复已有 `.workloop` episode，以及用户明确询问任务该如何推进时。

普通单步编辑、孤立小 Bug、独立 Review、纯问答、翻译和一次性文稿继续走 Host 的默认快速路径。

PDCA 控制流为：

```text
Goal Gate -> Plan Gate -> Dispatch/Do -> Check -> Act
```

Act 可以修复/关闭任务、记录 Skill 改进候选，或记录 Memory 候选；它不会在原任务中修改 Skill，也不会直接写入 Host Memory。

## 四条路线

| 路线 | 适用条件 |
|---|---|
| **Direct** | 用户明确调用后发现任务极小、可逆，diff 本身足以证明。 |
| **Verified** | 有或可以低成本增加确定性校验，且没有高风险信号。 |
| **Reviewed** | 高风险、完成标准主观，或确定性验证薄弱/缺失。 |
| **Distributed** | 必须跨会话恢复，或独立分片通过 Multi-Agent Cost gate。 |

Workloop 拥有路线、Gate、预算、状态与编排权；被委托的 Skill 只拥有当前阶段的技术方法。Host 原生编排与 Workloop Route 4 只能选择一个 owner，避免递归 Agent 树。

## 安全与证据

路线 2–4 创建 v3 episode：不可变 manifest、`goal.json`、`plan.json`、可变 state、append-only events、人类可读 contract、结构化 `checks.json`，以及 append-only 学习候选日志。旧的 v2 episode 仍可读取。

`scripts/validate-intent-plan` 会在以下条件满足前阻止执行：Goal 为 `clear` 或 `assumption_bounded`；每个 Goal criterion 映射到 Plan step 和 check；依赖图无环；Reviewed 任务有独立验证 owner；领域验证维度齐全；并行写入范围不重叠。`work.started` 与最终 grading 都会绑定 Goal、Plan 和 checks 摘要。

Profile 包括 `engineering`、`research`、`writing_design`、`personal_planning` 和 `high_stakes`。它们定义 Check 的最低维度，不授予权限，也不强制依赖专项 Skill。

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

验证器不经过 Shell，限制 cwd 不得逃逸仓库，强制 timeout，拒绝未填写模板及常见零测试假绿，输出成功命令的 stdout/stderr，并保存 grading artifact。新 manifest 绑定到 `episode.created`；`verification.passed` 绑定当前 checks、逐项 evidence 与 grading digest，`episode.closed` 会再次校验。Append-only events 仍是持久 write-ahead record。Host 的 sandbox、权限、网络策略和用户批准始终权威；验证器不是权限绕过通道。

## Trace 证据挖掘

`scripts/analyze-traces` 提供只依赖标准库的 OTLP JSONL 基线：流式读取受限输入，以 SHA-256 绑定源内容，识别保守的语义失败标记，输出真实 trace/span 引用与反例，并对照原始文件验证 direct 或 bounded-RLM 报告。它不会返回原始 payload、调用 Provider、编辑 Skill 或授权晋升。

小输入保持 `direct_baseline`。大型或跨运行语料可以成为 `bounded_rlm_candidate`，但这只表示应由现有 Cost gate 与 Host capability boundary 判断一层只读委派是否值得。无需安装或依赖 HALO；详见 `references/trace-evidence.md` 与 `evals/trace-analysis-contract.md`。

## 安装

运行时只需安装 `adaptive-workloop`。Waza、Superpowers、gstack 和 mattpocock/skills 是设计来源及可选专项能力，不是运行依赖。缺少专项 Skill 时使用 Host 原生 fallback，运行中不会隐式安装。

**Claude Code**（plugin marketplace）：

```bash
# 在 Claude Code 中执行
/plugin marketplace add wangsoft/adaptive-workloop
/plugin install adaptive-workloop@adaptive-workloop
```

**Codex**（从 GitHub 全局安装）：

```bash
npx skills add wangsoft/adaptive-workloop \
  --skill adaptive-workloop --agent codex --global --yes
```

其他 Agent Skills Host 可省略 `--agent codex`，按交互提示选择目标：

```bash
npx skills add wangsoft/adaptive-workloop
```

CLI 会记录 Git 来源，后续可直接更新：

```bash
npx skills update adaptive-workloop --global --yes
```

**手动 Git 兜底**（Codex）：

```bash
git clone https://github.com/wangsoft/adaptive-workloop.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/adaptive-workloop"
```

安装完成后新建一个 Codex 任务，让 Skill catalog 重新加载。

**Claude Desktop**：下载 release zip，在 Settings → Capabilities → Skills 上传。

Codex UI 元数据位于 `agents/openai.yaml`；Claude Code plugin manifest 位于 `.claude-plugin/`。确定性脚本需要 macOS/Linux + Python 3.10+。

## 命令

```bash
# 仓库事实，以及可选的 Host 能力清单
scripts/probe-capabilities . [--capabilities capabilities.json]

# 路线 2–4；Distributed 默认创建可追踪持久状态
scripts/create-episode --task "添加 CSV 导入器" --route verified \
  --profile engineering --model "unknown"

# 非仓库研究/规划使用显式 artifact root
scripts/create-episode --task "制定三个月搬迁计划" --route distributed \
  --profile personal_planning --dir /path/to/private-artifacts --model "unknown"

# goal.json、plan.json、contract.md 与 checks.json 填好后开始执行
scripts/validate-intent-plan .workloop/local/<episode-id>
scripts/episode-state .workloop/local/<episode-id> --status in_progress --kind work.started

# 严格结构化验证
scripts/verify-contract .workloop/local/<episode-id>

# 追加生命周期事件并更新可变状态
scripts/episode-state .workloop/local/<episode-id> \
  --status verified --kind verification.passed --evidence evidence/grading.json
scripts/episode-state .workloop/local/<episode-id> \
  --status complete --kind episode.closed

# 扫描 Distributed episode 的 Git 可见面，不输出命中的敏感值
scripts/check-episode .workloop/tracked/<episode-id>

# 追加证据绑定的候选；不会晋升 Skill 或 Memory
scripts/record-learning .workloop/local/<episode-id> \
  --kind memory --claim "可复用的有界结论" --scope project \
  --evidence evidence/grading.json --writer current-agent \
  --generalizability project --confidence 0.8 --dedupe-key reusable-bounded-claim

# 包与 Eval 校验
scripts/check
scripts/run-evals --validate

# 摘要绑定的 direct baseline，然后验证输出报告
scripts/analyze-traces --trace traces.jsonl --output trace-report.json
scripts/analyze-traces --trace traces.jsonl --validate-report trace-report.json

# 确定性发布目录、可复现 zip 与 SHA-256 校验和
scripts/package-skill
cat dist/adaptive-workloop.zip.sha256

# 对精确 previous/candidate checkout 验证一个已冻结的类型化提案
scripts/validate-proposal \
  --proposal .workloop/proposals/route-review-001.json \
  --registry evals/editable-surfaces.json \
  --previous-skill /path/to/adaptive-workloop-v0.4.0 \
  --candidate-skill . \
  --output /private/evals/route-review-001-validation.json

# 在没有可选专项 Skill 时验证四条路线
scripts/run-evals --suite standalone \
  --host-profile codex-standalone \
  --adapter <provider-adapter> \
  --output evals/runs/codex-standalone

# 收集、独立评分并比较 bare/previous/candidate 三个条件
export WORKLOOP_ADAPTER_MODEL=gpt-5.6-sol
export WORKLOOP_GRADER_MODEL=claude-fable-5
scripts/run-matrix --suite behavior --case bc-001 --trials 3 \
  --adapter evals/adapters/codex-cli \
  --grader evals/adapters/claude-grader \
  --grader-profile claude-code-fable-5-high \
  --previous-skill /path/to/adaptive-workloop-v0.4.0 \
  --model-profile codex-gpt-5.6-sol-high \
  --proposal-validation /private/evals/route-review-001-validation.json \
  --pass-env WORKLOOP_ADAPTER_MODEL --pass-env CODEX_HOME \
  --pass-env WORKLOOP_GRADER_MODEL --pass-env ANTHROPIC_API_KEY \
  --output evals/matrices/public

# 中断后以新 attempt 续跑，不覆盖已有证据
scripts/run-matrix <相同参数> --resume

# 两类私有 one-shot 证据必须使用封存入口及 mode-0600 数据文件
chmod 0600 /private/evals/behavior-held-out.json
scripts/run-sealed-matrix \
  --dataset /private/evals/behavior-held-out.json \
  --evidence-class held-out \
  --proposal-validation /private/evals/route-review-001-validation.json \
  --output /private/results/held-out \
  -- --suite behavior <相同 Provider 与矩阵参数>

# 在候选评测前初始化；记录每个 comparison 和候选关闭事件
scripts/search-ledger init --ledger /private/results/search.jsonl \
  --search-id route-review-001 \
  --base-skill-digest sha256:<previous-skill-digest>
scripts/search-ledger record --ledger /private/results/search.jsonl \
  --comparison evals/matrices/public/comparisons/attempt-001.json
scripts/search-ledger close --ledger /private/results/search.jsonl \
  --candidate-skill-digest sha256:<candidate-skill-digest> \
  --status selected --reason "通过冻结的四类证据计划"

# 决策最多进入 eligible_for_human_approval，不会自动晋升
scripts/decide-promotion --policy evals/promotion-policy.json \
  --comparison evals/matrices/public/comparisons/attempt-001.json \
  --comparison evals/matrices/held-in/comparisons/attempt-001.json \
  --comparison /private/results/held-out/comparisons/attempt-001.json \
  --comparison /private/results/audit-held-out/comparisons/attempt-001.json \
  --search-ledger /private/results/search.jsonl \
  --output evals/matrices/promotion-decision.json
```

## 状态存储

- Verified/Reviewed：`.workloop/local/` 是被忽略的本地运行状态。
- Distributed：`.workloop/tracked/` 的脱敏 manifest/Goal/Plan/state/events/contract/checks/progress/handoff/学习候选可进入 Git；runtime、能力快照、锁与 evidence 保持忽略。
- `.workloop/proposals/` 不被忽略，使改进提案能进入人工评审。

如果整个 workspace 本身会销毁，必须配置外部 issue/task store，不能仅凭本地文件声称“可持久恢复”。

## 目录

```text
adaptive-workloop/
├── SKILL.md
├── .claude-plugin/          # Claude Code plugin + marketplace manifest
├── agents/openai.yaml       # Codex UI 元数据
├── packaging.allowlist      # 精确发布载荷 (make package)
├── examples/                # 可重放、摘要绑定的 episode 快照
├── CHANGELOG.md · SECURITY.md · CONTRIBUTING.md
├── scripts/
│   ├── probe-capabilities
│   ├── analyze-traces
│   ├── create-episode
│   ├── validate-intent-plan
│   ├── verify-contract
│   ├── episode-state
│   ├── check-episode
│   ├── record-learning
│   ├── run-evals
│   ├── grade-evals
│   ├── compare-evals
│   ├── run-matrix
│   ├── run-sealed-matrix
│   ├── search-ledger
│   ├── validate-proposal
│   ├── decide-promotion
│   ├── package-skill
│   └── check
├── references/             # Goal/Plan、profiles、routes、verification、Action/learning、恢复与改进
├── assets/
│   ├── contract.md
│   ├── checks.json
│   ├── goal.json
│   ├── plan.json
│   ├── progress.md
│   └── handoff.md
├── evals/
│   ├── trigger-cases.json
│   ├── behavior-cases.json
│   ├── regression-cases.json
│   ├── standalone-cases.json
│   ├── trace-analysis-cases.json
│   ├── trace-analysis-contract.md
│   ├── profiles/codex-standalone.json
│   ├── adapters/codex-cli
│   ├── adapters/claude-code
│   ├── adapters/codex-grader
│   ├── adapters/claude-grader
│   ├── promotion-policy.json
│   ├── editable-surfaces.json
│   ├── proposal-contract.md
│   ├── matrix-protocol.md
│   ├── grader-contract.md
│   └── adapter-contract.md
└── tests/
```

## 评测

`scripts/run-evals` 校验全部公开套件，也能运行 provider-neutral adapter。每次运行都会写入自摘要 manifest，绑定 Skill checkout、adapter runtime、完整数据集、证据类别、选中用例、条件、model/host profile、trial 数、资源限制及显式传入的环境变量名。仓库内数据集固定为 `public`；外部数据集必须显式传入匹配的 `--evidence-class`，且文件内 `evidence_class` 与布尔 `held_out`/`audit_holdout` 必须一致，否则 fail closed。Adapter 子进程采用 deny-by-default 环境、合并输出上限、覆盖 stdin 与执行阶段的统一 timeout，以及整个进程组清理。发送给 adapter 的 request 不包含 expected label。

Trigger 和 standalone conformance 由 runner 精确评分。Standalone 产物必须真实存在于 runner 所有的 `artifact_root` 内，SHA-256 由 adapter 从普通文件重新计算，不信任模型提供的 hash 或路径声明。Behavior 与 Regression 保持 `review_required`，除非收集阶段明确使用 `--allow-review-required`。`scripts/grade-evals` 会重验全部源摘要、拒绝与 producer runtime 摘要相同的 grader，并把 review 写到独立目录而不覆盖原始 grading。`scripts/compare-evals` 只接受兼容且已完成的 run，输出通过率、Wilson 区间、pass@k、pass^k、usage、耗时及候选版本的配对增量。

`evals/adapters/codex-cli` 与 `evals/adapters/claude-code` 只把已绑定的 candidate/previous Skill 放入隔离 case workspace；`bare` 不安装 Skill。两者使用 CLI structured output，本地派生 artifact hash，并从 provider event instrumentation 而非模型自述派生 Skill 调用。内置 Codex 与 Claude grader 均运行在全新临时 workspace；Codex 使用只读 sandbox 并忽略项目规则，Claude 禁用工具、slash command、持久会话及未显式配置的 MCP。配置模型身份与 Provider 实际观察身份分开记录。

`scripts/validate-proposal` 把一个 failure-derived 改动绑定到一个类型化可编辑面，并拒绝受保护或未声明的 runtime 改动。`scripts/run-matrix` 是标准三条件编排器：执行前绑定脚本、adapter、grader、数据集、冻结提案、candidate/previous Skill 摘要、profile、资源上限及环境变量名。自摘要 append-only event chain 与编号 attempt 使 `--resume` 能在中断后继续，且不覆盖部分证据。非阻塞输出锁会拒绝并发 writer；owner-only JSON/log 通过原子替换写入，Provider/grader 持久化输出会按显式 secret 值和常见 secret 模式脱敏。这属于纵深防御，不是完整 DLP。`scripts/run-sealed-matrix` 为 held-out 与 audit-held-out 数据增加窄化的路径与文件权限边界。

`scripts/search-ledger` 把每个候选 comparison 及拒绝/选择事件写入 owner-only、带锁并 `fsync` 的摘要链，再重验引用 artifact。`scripts/compare-evals` 报告配对净胜数，以及只针对 discordant trials 的 Wilson 95% 区间。`scripts/decide-promotion` 读取已关闭 ledger 及被选候选的 public、held-in、held-out 与 audit-held-out comparison，检查目标 uplift、配对置信度、回归、全搜索候选/轮次/私有暴露和 trial/cost/time 预算、token/cost 比率、稳定的 Provider observed identity，以及与 producer 不同的 grader observed model；只输出 `rejected`、`inconclusive` 或 `eligible_for_human_approval`，并始终记录 `promotion_authorized=false`。身份分离是 provenance guard，不是认知独立性的证明。

`scripts/package-skill` 打包与 Skill digest 相同的 runtime surface，校验 progressive-disclosure 引用，写入 `release-manifest.json`，构建可复现 zip 并输出 SHA-256 校验和。发布包内的 `scripts/check` 会重验 manifest 中的每个文件；源 checkout 还会运行完整测试套件。

凭据、fixture root 与模型配置必须通过 `--pass-env` 点名；详见 `evals/provider-adapters.md` 与 `evals/matrix-protocol.md`。CI 只用 fake CLI 验证全部 adapter，不会调用真实模型，也不构成模型质量结论。

Standalone suite 固定 `installed_skills=[]`、`subagents=false`、`browser=false`，覆盖四条路线，拒绝 trace 中调用任何不可用 Skill，并要求缺少独立 verifier 的高风险任务停在 `needs_human`。它证明 fallback wiring，不代表真实模型质量。

对同一 fixture 分别运行 `bare`、绑定精确 `--previous-skill` checkout 的 `previous`、`candidate`，固定模型、Host、effort、tools、repository snapshot、grader 与 runtime envelope。进行重复 trial，比较 verified success、pass^k、人工介入、延迟、成本、回滚和事故，而不只比较路线文案。

仓库内用例（包括 Trace 分析 fixture）属于公开回归与 wiring 检查，不是真正 held-out 证据，也不能证明 RLM 优于 direct analysis。Stable 晋升需要 proposer 无法访问、彼此独立的私有 held-out 与 audit-held-out suite，完整的真实 Provider 成本证据，以及人工批准。

GitHub CI 在 Linux 的 Python 3.10、3.12、3.14 和 macOS 的 Python 3.12 上执行确定性 gate 与固定版本 Ruff；同时用固定版本 validator 校验 Agent Skills 规范和 Claude Code plugin manifest。运行时包本身仍然只依赖标准库。

## 模型策略

路由不依赖模型品牌。未知模型使用同样路线和 authority，只收紧验证节奏。只有实测的 model-plus-host 差异才能加入简短、会过期的 counter-instruction；active ledger 出厂为空。干净验证 streak 只能扩大当前 episode 的步长，不能生成永久模型 profile。

## 谱系

本设计组合了 harness-engineering 的实证控制、Waza 的克制、Superpowers 的独立验证、gstack 的 runtime discipline、mattpocock/skills 的可组合性，以及 HALO/RLM 的外置 Trace 分析，但不复制其完整工作流，也不依赖这些包。

## License

MIT
