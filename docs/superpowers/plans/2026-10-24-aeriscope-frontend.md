# AeriScope 高级研究前端 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为现有 Python SNN 研究流水线添加 FastAPI 和 React 高级交互驾驶舱。

**Architecture:** FastAPI 读取运行产物并计算序列/曲线/案例，React 仅消费 JSON。开发时 Vite 代理 API，生产时 FastAPI 托管静态构建。后台实验复用 `run_pipeline`，不在 JavaScript 中实现数据或模型逻辑。

**Tech Stack:** Python 3.11、FastAPI、Uvicorn、React、TypeScript、Vite、Recharts、Lucide React、原生 CSS。

**Spec:** `docs/superpowers/specs/2026-10-24-aeriscope-frontend-design.md`

## Global Constraints

- 数据处理和机器学习全部保留在 Python。
- 所有页面标明 observed/synthetic，不伪造真实空气数据。
- 不新增未要求的测试脚手架；使用真实 API、构建和浏览器验证。
- 保持现有 CLI 和产物兼容，不修改模型定义或默认研究事件。
- 语义 HTML、键盘焦点、响应式布局、减少动态效果和 API 错误状态必须实现。

## Review Focus

- 缺失/损坏 artifacts：明确错误而非空白假数据；API 冒烟验证。
- 20,000+ 预测点：PR 曲线在 Python 计算，原始序列下采样，避免浏览器过载。
- 实验并发/失败：单任务状态与错误信息清晰，不覆盖运行状态。
- 来源混淆：每个主视图可见数据来源，接口响应携带来源。
- 移动和键盘：导航、表单、图表控件可操作，无横向溢出。

### Task 1: FastAPI 产物与实验接口

**Files:** `src/changchun_air/web_api.py`、`pyproject.toml`、`requirements.txt`

- [ ] 先请求尚不存在的 `/api/health`，确认连接失败。
- [ ] 实现只读 artifacts 加载器，统一 JSON 异常和来源字段。
- [ ] 实现 dashboard、EDA、模型 PR 曲线、SNN 案例、报告接口。
- [ ] 实现项目内路径校验、UUID 输出、单后台实验和状态查询。
- [ ] 启动 Uvicorn，用真实 HTTP 断言全部接口与失败输入。

### Task 2: React 骨架和设计系统

**Files:** `frontend/package.json`、`vite.config.ts`、`tsconfig.json`、`index.html`、`src/main.tsx`、`src/App.tsx`、`src/styles.css`、`src/api.ts`、`src/types.ts`

- [ ] 创建 Vite/TypeScript 清单并安装依赖。
- [ ] 实现侧栏、顶栏、六视图导航、主题、响应式和跳转正文。
- [ ] 实现统一卡片、状态徽章、按钮、表单、加载/错误和焦点样式。
- [ ] 运行 TypeScript 构建，修正所有类型错误。

### Task 3: 数据研究视图

**Files:** `frontend/src/components/`、`frontend/src/pages/OverviewPage.tsx`、`DataPage.tsx`、`ModelsPage.tsx`

- [ ] 实现总览指标卡、模型对照、月度趋势和研究说明。
- [ ] 实现缺失率、PM2.5 序列、采暖季和滞后热图。
- [ ] 实现四模型 PR 曲线、指标切换和语义数据表。
- [ ] 验证空状态、加载和错误重试。

### Task 4: SNN、误差与实验视图

**Files:** `frontend/src/pages/SnnPage.tsx`、`CasesPage.tsx`、`ExperimentPage.tsx`

- [ ] 实现编码/网络结构、脉冲率、参数量和运行开销。
- [ ] 实现 TP/FN/FP 切换和预测起点/未来窗口图。
- [ ] 实现带标签的实验表单、状态轮询和完成刷新。
- [ ] 构建并通过界面启动真实合成实验。

### Task 5: 集成和浏览器验收

**Files:** `README.md`、上述文件的缺陷修复。

- [ ] 编写后端/前端开发启动与生产构建说明。
- [ ] 执行 Python 编译、npm build、全部 API 检查。
- [ ] 用内置浏览器检查六视图、控件、主题、移动端、控制台和网络。
- [ ] 独立代码审查并修复 Critical/Important，再重跑完整验收。
