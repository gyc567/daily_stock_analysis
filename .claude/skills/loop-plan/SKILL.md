# Loop Plan Skill

生成 Changelog 草稿和计划文档。

## 触发条件

- PR 合并到 main
- Release 准备
- 手动触发

## 输入

- 合并的 PR 列表
- Commit 历史
- 当前版本号

## 输出

```markdown
## [Unreleased] YYYY-MM-DD

### 新功能
- ...

### 改进
- ...

### 修复
- ...

### 文档
- ...
```

## 约束

- 遵循 `CHANGELOG.md` 的扁平格式
- 不自动发布
- 人类审核后才能更新正式文档
- 遵循 `LOOP_CONSTRAINTS.md`
