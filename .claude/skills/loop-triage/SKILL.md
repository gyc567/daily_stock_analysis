# Loop Triage Skill

分类 Issue 和 PR，判断优先级和处理方式。

## 触发条件

- Daily Triage workflow 运行
- 手动 `workflow_dispatch` 触发

## 输入

- Issue 列表（未关闭）
- PR 列表（开放）
- 最近提交历史（7 天）

## 处理流程

1. **分类 Priority**
   - P0: 安全漏洞、生产环境崩溃、数据丢失
   - P1: 功能缺失、严重影响使用、CI 持续失败
   - P2: 优化、改进建议、bug（不影响主流程）
   - P3: 低优先级、nice to have

2. **分类 Type**
   - bug: Bug 报告
   - feature: 功能请求
   - docs: 文档问题
   - infra: 基础设施
   - question: 问题

3. **判断处理方式**
   - auto-fix: 可自动修复（L2）
   - needs-review: 需要人类 review
   - blocked: 等待其他 issue/PR
   - wontfix: 建议关闭
   - good-first-issue: 适合新贡献者

## 输出

更新 `STATE.md`:
- 高优先级列表
- 观察列表
- 建议动作

## 约束

- 遵循 `LOOP_CONSTRAINTS.md`
- 不修改任何代码
- 不关闭任何 Issue/PR
- 不添加/删除 labels
- 不推送代码
