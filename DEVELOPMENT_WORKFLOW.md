# 开发工作流程梳理

基于 SDD（规范驱动开发）和 TDD（测试驱动开发）的完整开发流程。

## 一、SDD 工作流：从意图到实现

### 1.1 工作流阶段

```
模糊想法 → spec.md → plan.md → tasks.md → 代码实现
  (WHAT)    (WHAT)    (HOW)     (ACTIONS)  (CODE)
```

### 1.2 各阶段职责

#### Stage 1: 需求与设计（spec.md）
- **角色**：需求编译器
- **输入**：模糊想法、痛点、目标
- **输出**：`spec.md`（可执行规范）
- **关键活动**：
  - 多轮澄清需求（AI 提问，人回答）
  - 明确 MVP 边界（做减法）
  - 定义验收标准（可测试用例）
  - 输出格式示例（YAML frontmatter）

#### Stage 2: 计划与任务（plan.md + tasks.md）
- **角色**：工作流指挥家
- **输入**：`spec.md` + `constitution.md` + 技术约束
- **输出**：
  - `plan.md`（技术方案、架构分解）
  - `tasks.md`（原子任务清单）
- **关键活动**：
  - AI 生成 plan.md（架构师角色）
  - AI 生成 tasks.md（技术组长角色）
  - **人工审查**（最重要！）
  - 任务依赖分析
  - 并行标记 `[P]`

#### Stage 3: 编码与测试（TDD）
- **角色**：现场总指挥 + 质量监督者
- **输入**：`tasks.md`
- **输出**：可运行代码 + 测试
- **关键活动**：
  - 按 tasks 逐条执行
  - **严格 TDD**：Red → Green → Refactor
  - 审查测试与关键变更
  - 维护 spec 作为权威依据

## 二、TDD 开发流程（每个功能）

### 2.1 TDD 三阶段循环

```
Red → Green → Refactor
 ↓      ↓        ↓
测试  实现    优化
```

#### Red 阶段：先写失败测试
- **目标**：把需求固化为可执行约束
- **作用**：给 AI 的"真理边界"，防止自作主张
- **要求**：
  - 表格驱动测试（table-driven tests）
  - 覆盖多种场景（正常、边界、错误）
  - 测试必须失败（预期行为）

#### Green 阶段：最小实现
- **目标**：让测试通过
- **原则**：
  - 只写够用的逻辑
  - 不要"顺手做更多"
  - 控制复杂度，避免过度工程

#### Refactor 阶段：受保护重构
- **目标**：优化结构，提升可读性
- **前提**：测试全绿
- **活动**：
  - 抽取函数
  - 优化命名
  - 改进结构
  - 避免在第一次实现时堆叠复杂性

### 2.2 TDD 的关键原则

1. **先测试后实现**：避免 AI 的"自洽幻觉"
   - 如果同时写实现和测试，AI 可能写错实现，再写配合错误实现的测试
   - 先写测试并审查，相当于建立"真理边界"

2. **维护意图单一来源**：Spec 是权威
   - **意图偏差**（需求没想清楚）→ 回到 `spec.md` 修正
   - **实现偏差**（实现写错了）→ 直接修代码，不动 spec

## 三、具体开发工作清单（按 Phase）

### Phase 1: 核心基础设施（Week 1-2）

#### 1.1 项目骨架搭建
**工作流程**：
1. **创建项目结构**（一次性）
   - 创建所有目录（`claude_code/`, `tests/` 等）
   - 创建 `__init__.py` 文件
   - 创建 `setup.py`、`README.md`

2. **依赖管理**（一次性）
   - 创建 `requirements.txt`（精确版本）
   - 创建 `requirements-frozen.txt`（锁定版本）
   - 验证 Python 3.8.10 兼容性

3. **基础 CLI 框架**（TDD）
   - **Red**：写测试 `tests/test_cli.py`
     - 测试 CLI 入口点
     - 测试基本命令结构
     - 测试帮助信息
   - **Green**：实现 `cli/main.py`
     - 使用 `click==7.1.2`
     - 创建基础命令结构
   - **Refactor**：优化代码结构

4. **终端美化库集成**（TDD）
   - **Red**：写测试
     - 测试 Rich 输出（Markdown、代码高亮、表格）
     - 测试 Prompt Toolkit 输入（历史记录、补全）
     - 测试 Questionary 菜单（选择、确认）
     - 测试 Colorama 颜色支持（Windows 7）
   - **Green**：实现
     - 集成 Rich（`rich.console.Console`）
     - 集成 Prompt Toolkit（`prompt_toolkit.PromptSession`）
     - 集成 Questionary（`questionary.select`, `questionary.confirm`）
     - 初始化 Colorama（`colorama.init()`）
   - **Refactor**：封装为工具函数

#### 1.2 LLM 集成（TDD）

**工作流程**：

1. **抽象接口设计**（TDD）
   - **Red**：写测试 `tests/test_llm_client.py`
     - 测试 `LLMClient` 接口方法
     - 测试工厂模式创建
     - 测试自动回退机制
   - **Green**：实现
     - `llm/client.py`：定义抽象基类（ABC）
     - `llm/factory.py`：实现工厂模式
   - **Refactor**：优化接口设计

2. **OpenAIClient 实现**（TDD）
   - **Red**：写测试 `tests/test_openai_client.py`
     - 测试 `chat_completion()`（非流式）
     - 测试流式响应
     - 测试工具调用（Function Calling）
     - 测试错误处理
     - 测试内网端点配置
   - **Green**：实现 `llm/openai_client.py`
     - 使用 `openai==0.28.1`
     - 实现所有接口方法
   - **Refactor**：优化错误处理

3. **RequestsClient 实现**（备选，TDD）
   - **Red**：写测试 `tests/test_requests_client.py`
     - 测试手动实现 OpenAI 格式请求
     - 测试 SSE 流式响应解析
     - 测试重试策略
   - **Green**：实现 `llm/requests_client.py`
     - 使用 `requests==2.28.2`
     - 手动实现所有功能
   - **Refactor**：优化代码结构

#### 1.3 配置系统（TDD）

1. **分层配置加载器**（TDD）
   - **Red**：写测试 `tests/test_config_loader.py`
     - 测试用户全局配置加载
     - 测试项目共享配置加载
     - 测试项目本地配置加载
     - 测试配置合并优先级
     - 测试 Windows 7 用户目录处理
   - **Green**：实现 `config/loader.py`
     - 实现分层加载逻辑
     - 处理 Windows 7 路径（`%USERPROFILE%` vs `~`）
   - **Refactor**：优化配置合并逻辑

### Phase 2: 交互模型（Week 2-3）

#### 2.1 上下文注入（`@`）（TDD）

1. **交互解析器**（TDD）
   - **Red**：写测试 `tests/test_parser.py`
     - 测试 `@file` 文件引用解析
     - 测试 `@dir` 目录引用解析
     - 测试路径补全
     - 测试相对路径与绝对路径
     - 测试 Git 感知（`.gitignore` 过滤）
   - **Green**：实现 `interaction/parser.py`
     - 实现路径解析
     - 实现 Git 感知（读取 `.gitignore`）
   - **Refactor**：优化解析逻辑

2. **上下文格式化**（TDD）
   - **Red**：写测试
     - 测试文件内容读取与格式化
     - 测试目录结构树生成
     - 测试上下文标记
   - **Green**：实现
     - 文件内容格式化
     - 目录树生成
   - **Refactor**：优化格式化逻辑

#### 2.2 命令执行（`!`）（TDD）

1. **命令执行器**（TDD）
   - **Red**：写测试 `tests/test_executor.py`
     - 测试 PowerShell 命令执行（Windows 7）
     - 测试 bash 命令执行（Unix）
     - 测试输出捕获（stdout/stderr）
     - 测试编码处理（UTF-8）
     - 测试错误码处理
     - 测试工作目录设置
     - 测试路径转换（Windows 7）
   - **Green**：实现 `core/executor.py`
     - 使用 `subprocess` 模块
     - Windows 7 使用 `powershell.exe -Command`
     - Unix 使用 `/bin/bash -c`
     - 正确处理编码（UTF-8）
   - **Refactor**：优化错误处理

#### 2.3 基础 Agent 循环（TDD）

1. **Agent 引擎**（TDD）
   - **Red**：写测试 `tests/test_agent.py`
     - 测试对话管理（消息历史）
     - 测试工具调用处理
     - 测试上下文注入
     - 测试命令执行集成
     - 测试安全检查与审批
   - **Green**：实现 `core/agent.py`
     - 实现对话循环
     - 集成上下文注入
     - 集成命令执行
     - 集成终端美化（Rich）
     - 集成交互式输入（Prompt Toolkit/Questionary）
   - **Refactor**：优化架构设计

### Phase 3-8: 后续阶段（类似流程）

每个功能模块都遵循相同的 TDD 流程：
1. **Red**：先写测试（表格驱动，覆盖多种场景）
2. **Green**：最小实现（让测试通过）
3. **Refactor**：优化结构（在测试保护下）

## 四、开发工作检查清单

### 4.1 开始开发前

- [ ] 阅读并理解 `spec.md`（如果存在）
- [ ] 阅读并理解 `plan.md`（如果存在）
- [ ] 阅读并理解 `tasks.md`（如果存在）
- [ ] 阅读 `constitution.md`（项目宪法）
- [ ] 确认技术栈和依赖版本

### 4.2 开发每个功能时

- [ ] **先写测试**（Red 阶段）
  - [ ] 表格驱动测试（多种场景）
  - [ ] 测试必须失败（预期）
  - [ ] 审查测试用例是否完整
- [ ] **再写实现**（Green 阶段）
  - [ ] 最小实现（只写够用的）
  - [ ] 让所有测试通过
  - [ ] 不要"顺手做更多"
- [ ] **最后重构**（Refactor 阶段）
  - [ ] 优化代码结构
  - [ ] 提升可读性
  - [ ] 抽取函数/类
  - [ ] 确保测试仍然通过

### 4.3 完成功能后

- [ ] 运行所有测试（`pytest`）
- [ ] 检查代码覆盖率
- [ ] 审查是否符合 `constitution.md`
- [ ] 更新文档（如果需要）
- [ ] 提交代码（清晰的 commit message）

## 五、关键原则总结

### 5.1 SDD 原则

1. **规范是真理之源**：`spec.md` 是唯一权威
2. **人工审查关键**：plan.md 和 tasks.md 必须审查
3. **做减法**：MVP 边界要清晰
4. **意图偏差 vs 实现偏差**：
   - 意图偏差 → 修正 spec.md
   - 实现偏差 → 直接修代码

### 5.2 TDD 原则

1. **先测试后实现**：避免 AI 自洽幻觉
2. **表格驱动测试**：覆盖多种场景
3. **最小实现**：只写够用的代码
4. **测试保护重构**：在测试全绿时重构

### 5.3 工程实践

1. **Python 3.8.10 严格兼容**：不使用新特性
2. **Windows 7 兼容性**：路径、编码、命令执行
3. **内网环境考虑**：离线安装、证书验证
4. **代码审查**：每个关键变更都要审查

## 六、开发顺序建议

### 6.1 第一阶段：基础设施（必须优先）

1. 项目骨架（目录结构、依赖）
2. 配置系统（分层加载）
3. LLM 集成（抽象接口 + 一种实现）
4. 基础 CLI（入口点）

### 6.2 第二阶段：核心交互（MVP 核心）

1. 上下文注入（`@`）
2. 命令执行（`!`）
3. Agent 循环（整合所有功能）

### 6.3 第三阶段：增强功能

1. 长期记忆（CLAUDE.md 等）
2. 工作流封装（Commands、Hooks）
3. 安全体系（Permissions、Checkpointing）

### 6.4 第四阶段：高级功能

1. SDD 引擎（spec → plan → tasks）
2. 扩展能力（MCP、Skills、Subagents）
3. 编程接口（Headless 模式）

## 七、每个任务的开发模板

```python
# 1. Red 阶段：写测试
# tests/test_feature.py
def test_feature_normal_case():
    """测试正常情况"""
    # 准备
    # 执行
    # 断言

def test_feature_edge_case():
    """测试边界情况"""
    # ...

def test_feature_error_case():
    """测试错误情况"""
    # ...

# 2. Green 阶段：写实现
# claude_code/feature.py
class Feature:
    def method(self):
        # 最小实现
        pass

# 3. Refactor 阶段：优化
# 在测试保护下重构
```

## 八、注意事项

1. **不要跳过测试**：每个功能都要先写测试
2. **不要同时写测试和实现**：严格按 Red → Green → Refactor
3. **不要修改 spec**：除非是意图偏差
4. **不要过度工程**：只实现 spec 要求的功能
5. **保持简单**：遵循 constitution.md 的简单性原则

---

**最后更新**: 2024-12-19
**参考文档**: 
- 17-需求与设计.md
- 18-计划与任务.md
- 19-编码与测试.md

