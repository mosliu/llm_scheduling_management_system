# 用户侧简化研判页

新增了一个独立于 `/console` 的用户页面：`GET /briefing`。

设计目标：

- 面向不需要理解模板、执行引擎、配置项的使用者
- 只暴露必要能力：输入内容、勾选搜索项、查看进度、读取结果
- 页面顶部允许直接修改 API 基地址，适配 `http://172.23.16.175:8000` 这类部署地址

交互流程：

1. 页面加载时读取 `/api/v1/provider-catalog/search`，展示可勾选搜索项
2. 用户提交后调用 `POST /api/v1/reports/public-opinion`
3. 当请求体中 `auto_start=true` 时，服务端会在后台自动启动该任务
4. 页面轮询 `/api/v1/tasks/{task_id}` 获取进度
5. 任务完成后读取 `/api/v1/reports/public-opinion/{task_id}/final-report`

兼容性说明：

- 原有 `/console` 路径和控制台交互不受影响
- `POST /api/v1/reports/public-opinion` 新增 `auto_start` 字段，默认仍为 `false`
