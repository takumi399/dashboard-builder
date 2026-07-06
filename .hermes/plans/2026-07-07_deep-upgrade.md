# Dashboard Builder 深度升级 — 实施计划

> **目标：** 把 dashboard-builder 从「15 提交 0 测试的雏形」升级为「50+ 提交、有测试、有协作编辑、有 SQL 数据源的硬核全栈项目」

> **协作模式：** Hermes 写 prompt.txt → Claude Code (`-p`) 执行 → Hermes 验证结果

---

## 现状分析

```
后端：FastAPI + SQLAlchemy async + SQLite，4 个 API 路由，3 个数据模型
前端：React 18 + TS + Vite + Antd 5 + ECharts 5 + react-rnd + Zustand
测试：0（backend/tests/__init__.py 是空文件）
数据源：仅支持 CSV 上传
协作：无（单人编辑）
图表类型：bar, line, pie（3 种）
```

---

## 升级路线

### Phase 1：测试基础设施（测试覆盖率从 0 → 60%+）

**目标：** 后端所有 API 端点有集成测试，核心逻辑有单元测试

**任务：**
1. 配置 pytest + pytest-asyncio + httpx AsyncClient
2. 后端 models 单元测试（Dashboard, Chart, DataSource 字段验证）
3. 后端 API 集成测试（auth 注册/登录、dashboard CRUD、datasource 上传/查询）
4. GitHub Actions CI（每次 push 自动跑测试）
5. 前端 vitest + React Testing Library 基础组件测试

---

### Phase 2：SQL 数据源（从 CSV-only → 支持数据库直连）

**目标：** 用户可以连接自己的 MySQL/PostgreSQL 数据库，写 SQL 查询作为图表数据源

**任务：**
1. 后端：新增 `source_type=sql` 数据源，存储连接信息（host/port/user/password/db）
2. 后端：新增 `/api/datasources/{id}/execute` 端点，执行 SQL 并返回结果
3. 前端：数据源创建页面新增「数据库连接」Tab
4. 前端：SQL 查询编辑器（@monaco-editor/react 代码高亮 + 自动补全）
5. 前端：查询结果预览表格 + 绑定到图表
6. SQL 注入防护（参数化查询 + 关键字黑名单）

---

### Phase 3：实时协作编辑

**目标：** 多人同时编辑同一个看板，看到彼此的拖拽操作

**任务：**
1. 后端：FastAPI WebSocket 端点 `/ws/dashboards/{id}`
2. 后端：房间管理（ConcurrentHashMap 模式，跟踪哪些用户在编辑哪些看板）
3. 前端：useWebSocket hook + 操作广播（图表增删、移动、缩放）
4. 前端：协作光标/头像指示器（谁在编辑）
5. 冲突处理：最后写入者胜出（简单方案），记录操作日志

---

### Phase 4：图表增强 & 性能优化

**目标：** 更多图表类型 + 大数据量流畅渲染

**任务：**
1. 新增图表类型：散点图、热力图、雷达图、仪表盘
2. 自定义 ECharts option JSON 编辑器（高级用户直接写配置）
3. 大数据量数据采样（>10000 点自动降采样）
4. 前端：React.memo + useMemo 优化不必要的重渲染
5. 后端：数据分页 + 游标查询

---

## 执行顺序

```
Phase 1 → Phase 2 → Phase 3 → Phase 4

每个 Phase 内的任务逐个执行，每个任务完成后 git commit
```

## 预计提交数

```
Phase 1: ~12 commits（测试文件 + CI 配置）
Phase 2: ~10 commits（SQL 数据源 + 编辑器）
Phase 3: ~12 commits（WebSocket + 协作）
Phase 4: ~10 commits（图表 + 优化）
总计: ~44 commits，加上现有 15 = ~59 commits
```
