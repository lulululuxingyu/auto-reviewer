---
compiled: false
date: '2026-04-29T14:20:42+08:00'
kind: reference
marks: []
read_count: 0
slug: prd_v2
source: chat:untitled:assistant#1
summary: ''
tags:
- raw/reference
---

根据我们最近的架构决策，初始PRD中的“高层架构”部分已经过时了。以下是结合我们讨论更新后的版本。

---

# 产品需求文档 (PRD): Auto-Reviewer Agent

### 1. 目标

*   **自动化**: 自动响应 GitHub 上的事件，特别是针对需要设计审查的 Issue 和需要代码审查的 Pull Request。
*   **效率**: 利用自动化流程，快速提供初步的、由 LLM 生成的审查意见。
*   **集成**: 无缝集成到现有的 GitHub 工作流中，不干扰人类审查者。
*   **本地化**: 支持在本地环境中运行核心的 LLM 推理服务（`codex` CLI）。

### 2. 功能需求

*   **设计审查**:
    *   当一个 GitHub Issue 被添加特定标签（例如 `design-needed`）时，系统应被触发。
    *   系统获取该 Issue 的标题和内容。
    *   调用 `codex` CLI，生成设计方案。
    *   将生成的设计方案作为评论发布到该 Issue 下。

*   **代码审查**:
    *   当一个 Pull Request 被创建或更新时，系统应被触发。
    *   系统获取该 PR 的 diff（变更内容）。
    *   调用 `codex` CLI，对 diff 内容进行审查。
    *   将审查结果作为评论发布到该 PR 下。

*   **身份标识**:
    *   所有由本系统发布的评论都必须清晰地标识为机器人生成。
    *   这通过使用一个专门的机器人账户（例如 `my-org-bot`）或通过 GitHub Actions 的默认机器人身份（`github-actions[bot]`）来实现。
    *   评论内容本身也应包含明确的机器人标识，例如 "🤖 Auto-Reviewer:"。

### 3. 高层架构 (已更新)

系统将作为 **GitHub Actions 工作流** 实现，而不是一个独立的 Web 服务。

1.  **事件触发**: 工作流由 GitHub 仓库中的 `pull_request` 和 `issues` 事件触发。
2.  **自托管 Runner (Self-hosted Runner)**:
    *   为了访问部署在本地的 `codex` CLI，将在同一台服务器上配置一个自托管的 GitHub Actions Runner。
    *   所有审查作业都将路由到这个 Runner 上执行。
3.  **执行脚本**:
    *   工作流将运行一个 Python 脚本。
    *   该脚本负责：
        *   从事件上下文中解析出 PR 或 Issue 的详细信息。
        *   格式化适用于 `codex` CLI 的输入。
        *   执行 `codex` CLI 命令并捕获其输出。
        *   使用 GitHub API 将输出结果作为评论发布回去。

### 4. 非功能性需求

*   **安全性**: 避免在代码库中硬编码敏感信息。使用 GitHub Actions 的 `secrets` 来管理必要的令牌。
*   **可配置性**: 仓库名称、触发审查的 Issue 标签等应作为可配置的输入项。

---

这个更新后的版本准确地反映了我们最新的架构决策：**使用 GitHub Actions 和自托管 Runner**。
