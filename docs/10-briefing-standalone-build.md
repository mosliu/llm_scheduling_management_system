# 单文件用户页导出说明

本文说明如何把用户侧研判页面导出为一个独立的单文件 `HTML`。

## 产物位置

- 导出脚本：[scripts/export_briefing_html.py](/E:/workspace_python/llm_scheduling_management_system/scripts/export_briefing_html.py:1)
- 导出结果：[briefing-standalone.html](/E:/workspace_python/llm_scheduling_management_system/docs/briefing-standalone.html)

## 生成命令

在仓库根目录执行：

```powershell
uv run python scripts/export_briefing_html.py
```

脚本会直接把当前页面源码导出成：

```text
docs/briefing-standalone.html
```

## 页面特性

- 单文件 HTML
- 通过 Vue CDN 运行，不依赖本地前端构建链
- 可以本地直接打开
- 页面中可配置 API 基地址
- 页面中可填写访问密码，自动作为 `X-LSMS-Password` 请求头发送
- 支持输入内容、勾选搜索项、轮询任务进展、展示最终结果

## 使用方式

1. 双击打开 `docs/briefing-standalone.html`
2. 在“接口地址”里填 API 地址，例如：`http://172.23.16.175:8000`
3. 如果接口启用了访问控制，在“访问密码”里填对应密码
4. 输入研判内容
5. 勾选搜索项
6. 点击“开始检索并整理”

## 关于“编译”

这里的“编译”本质上不是打包 Vue 工程，而是把仓库里的页面源码导出为一个单独 HTML 文件。

原因：

- 当前页面使用的是 Vue 全局版 CDN，不依赖 Vite / Webpack
- 页面本身已经是完整 HTML 字符串
- 所以最稳定的交付方式就是导出单文件，而不是额外引入前端构建系统

## 远程 API 调用限制

如果 `briefing-standalone.html` 是直接本地打开，再去请求远端 API，例如 `http://172.23.16.175:8000`，浏览器会按跨域规则处理。

这意味着：

- 如果服务端没有开启 CORS，静态页可能会被浏览器拦截
- 如果服务端开启了访问控制，必须填写页面中的“访问密码”

当前仓库里访问控制是通过 `X-LSMS-Password` 请求头完成的，因此已经兼容单文件页输入密码后访问。

要让本地打开的单文件页访问远端 API，服务端还必须开启 CORS。建议在 `config/app.toml` 中增加：

```toml
[api]
host = "0.0.0.0"
port = 8000

[api.cors]
enabled = true
allow_origins = ["*"]
allow_methods = ["*"]
allow_headers = ["*"]
allow_credentials = false
max_age = 600
```

然后重启 API 服务。

说明：

- `allow_origins = ["*"]` 可以覆盖 `file://` 打开的单文件页
- 如果你希望只允许固定来源，也可以把 `["*"]` 改成明确的域名列表
- 若使用当前仓库的访问控制，浏览器预检 `OPTIONS` 现在会被放行，单文件页可以携带 `X-LSMS-Password`

## 推荐做法

有两种可用方式：

1. 最稳妥：把这个 HTML 和 API 放在同域下提供访问
2. 纯静态方式：本地打开 HTML，然后在页面里填写远端 API 地址和访问密码

如果你后面要长期作为独立静态页对外发放，建议再给 API 增加明确的 CORS 白名单配置。
