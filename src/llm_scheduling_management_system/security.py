from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from html import escape
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

from llm_scheduling_management_system.config_loader import load_access_config
from llm_scheduling_management_system.config_models import AccessConfig, AccessCredentialConfig
from llm_scheduling_management_system.logging import logger


@dataclass(frozen=True)
class AuthenticatedUser:
    """认证成功后的用户信息数据结构。

    用途:
        保存通过身份验证的用户标识及认证密码的来源。

    用法:
        作为一个不可变的只读数据类，并在认证成功后存储到 HTTP 请求状态 `request.state` 中。

    @Author: mosliu
    """
    user: str
    password_source: str


def _cookie_token_for_credential(credential: AccessCredentialConfig) -> str:
    """为用户凭证生成 Cookie 校验 Token。

    用途:
        对用户名和密码计算 SHA-256 哈希值，并拼接为形如 "用户名:哈希值" 的字符串，用于客户端 Cookie 的值。

    用法:
        value = _cookie_token_for_credential(credential)

    @Author: mosliu
    """
    digest = hashlib.sha256(f"{credential.user}:{credential.password}".encode("utf-8")).hexdigest()
    return f"{credential.user}:{digest}"


def _resolve_user_from_password(config: AccessConfig, supplied_password: str, password_source: str) -> AuthenticatedUser | None:
    """通过明文密码匹配并解析已认证的用户。

    用途:
        在配置的凭证列表中查找匹配的密码，如果找到，返回带有用户名和来源信息的 AuthenticatedUser 对象。

    用法:
        user = _resolve_user_from_password(config, "mypassword", "header")

    @Author: mosliu
    """
    for credential in config.credentials:
        if secrets.compare_digest(credential.password, supplied_password):
            return AuthenticatedUser(user=credential.user, password_source=password_source)
    return None


def _resolve_user_from_cookie(config: AccessConfig, cookie_value: str | None) -> AuthenticatedUser | None:
    """通过 Cookie 解析已认证的用户。

    用途:
        从请求传入的加密 Cookie 串中比对是否有匹配的用户凭证 Token，如有则返回对应的 AuthenticatedUser。

    用法:
        user = _resolve_user_from_cookie(config, "user:hash_token")

    @Author: mosliu
    """
    if not cookie_value:
        return None

    for credential in config.credentials:
        if secrets.compare_digest(_cookie_token_for_credential(credential), cookie_value):
            return AuthenticatedUser(user=credential.user, password_source="cookie")
    return None


def _render_login_page(config: AccessConfig, next_path: str, message: str | None = None) -> HTMLResponse:
    """渲染并返回系统的 HTML 登录页面。

    用途:
        在未登录但请求需要 HTML 返回时，向客户端展示简约的登录认证页面。

    用法:
        return _render_login_page(config, "/console")

    @Author: mosliu
    """
    safe_next_path = quote(next_path or "/console", safe="/?=&-_:.#")
    safe_message = escape(message or "")
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(config.basic_auth_realm)} Access</title>
  <style>
    :root {{
      --bg: #eef2f7;
      --panel: rgba(255,255,255,.92);
      --ink: #101828;
      --muted: #667085;
      --line: rgba(15, 23, 42, .1);
      --accent: #0071e3;
      --danger: #d92d20;
      --shadow: 0 24px 60px rgba(15, 23, 42, .12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
      color: var(--ink);
      font-family: "SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(0,113,227,.14), transparent 28%),
        linear-gradient(180deg, #f8f9fb 0%, var(--bg) 100%);
    }}
    .card {{
      width: min(100%, 420px);
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      padding: 28px;
      backdrop-filter: blur(24px);
    }}
    h1 {{ margin: 0 0 12px; font-size: 30px; letter-spacing: -.03em; }}
    p {{ margin: 0 0 18px; color: var(--muted); line-height: 1.5; }}
    label {{ display: block; margin-bottom: 8px; font-size: 13px; font-weight: 600; color: var(--muted); }}
    input {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 13px 14px;
      font: inherit;
    }}
    button {{
      width: 100%;
      margin-top: 14px;
      border: 0;
      border-radius: 999px;
      padding: 12px 16px;
      color: white;
      font: inherit;
      font-weight: 600;
      cursor: pointer;
      background: linear-gradient(180deg, #1492ff 0%, var(--accent) 100%);
    }}
    .message {{
      min-height: 20px;
      margin-top: 12px;
      color: var(--danger);
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <section class="card">
    <h1>Enter Password</h1>
    <p>Provide the configured access password. The server will map it to the matching user automatically.</p>
    <form id="loginForm">
      <label for="password">Password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" autofocus required />
      <button type="submit">Continue</button>
      <div id="message" class="message">{safe_message}</div>
    </form>
  </section>
  <script>
    const form = document.getElementById('loginForm');
    const passwordInput = document.getElementById('password');
    const message = document.getElementById('message');
    form.addEventListener('submit', async event => {{
      event.preventDefault();
      message.textContent = '';
      const response = await fetch('/auth/login', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ password: passwordInput.value, next: '{safe_next_path}' }}),
      }});
      if (!response.ok) {{
        const payload = await response.json().catch(() => ({{}}));
        message.textContent = payload?.detail?.message || 'Login failed.';
        passwordInput.focus();
        passwordInput.select();
        return;
      }}
      const payload = await response.json();
      window.location.href = payload.redirect_to || '{safe_next_path}';
    }});
  </script>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=401)


def _wants_html_login(request: Request) -> bool:
    """检查当前请求是否倾向于获取 HTML 响应。

    用途:
        通过判断 HTTP 方法为 GET 且请求头 Accept 中包含 "text/html" 或 "*/*"，且排除了特定的 API/健康检查接口。

    用法:
        if _wants_html_login(request): ...

    @Author: mosliu
    """
    if request.method != "GET":
        return False

    if request.url.path.startswith("/api/") or request.url.path == "/healthz":
        return False

    accept = request.headers.get("Accept", "")
    return "text/html" in accept or "*/*" in accept


def _resolve_authenticated_user(config: AccessConfig, request: Request) -> AuthenticatedUser | None:
    """从请求中解析并查找已认证的用户实体。

    用途:
        优先通过指定的 HTTP Header 进行密码校验；若 header 无密码，则尝试解析并校验 Cookie。

    用法:
        user = _resolve_authenticated_user(config, request)

    @Author: mosliu
    """
    header_name = config.password_header_name
    header_password = request.headers.get(header_name)
    if header_password:
        authenticated_user = _resolve_user_from_password(config, header_password, "header")
        if authenticated_user is not None:
            return authenticated_user

    return _resolve_user_from_cookie(config, request.cookies.get(config.session_cookie_name))


def _unauthorized_response(config: AccessConfig, request: Request) -> JSONResponse | HTMLResponse:
    """生成未授权响应实体。

    用途:
        若请求想要 HTML，则返回登录页的 HTML 响应，否则返回 401 状态码的 JSON 错误信息。

    用法:
        return _unauthorized_response(config, request)

    @Author: mosliu
    """
    if _wants_html_login(request):
        return _render_login_page(config, request.url.path)

    return JSONResponse(
        status_code=401,
        content={
            "detail": {
                "code": "authentication_required",
                "message": (
                    "Access denied. Provide the configured access password through "
                    f"the {config.password_header_name} header."
                ),
            }
        },
    )


def register_access_control(app) -> None:
    """在 FastAPI 应用上注册全局访问控制逻辑及认证相关 API 接口。

    用途:
        如果全局配置了访问控制，则会在应用上挂载 `/auth/login` 与 `/auth/logout` 路由，并注册全局的鉴权中间件。

    用法:
        在创建 FastAPI 实例后调用 register_access_control(app)。

    @Author: mosliu
    """
    config = load_access_config()

    if not config.enabled:
        logger.info("Access control disabled; HTTP endpoints are available without authentication.")
        return

    logger.info(
        "Access control enabled with {} configured credential(s); header auth uses {}.",
        len(config.credentials),
        config.password_header_name,
    )

    @app.post("/auth/login")
    async def access_login(request: Request) -> JSONResponse:
        """处理表单提交的登录请求。

        用途:
            校验用户提交的密码，若正确，则在响应中设置 Session Cookie 并返回重定向目标地址。

        用法:
            客户端 POST 发送包含密码的 JSON 到 `/auth/login`。

        @Author: mosliu
        """
        payload = await request.json()
        submitted_password = str(payload.get("password", ""))
        next_path = str(payload.get("next", "/console") or "/console")
        authenticated_user = _resolve_user_from_password(config, submitted_password, "password_form")
        if authenticated_user is None:
            logger.warning("Rejected login attempt for next={} from unauthenticated client", next_path)
            return JSONResponse(
                status_code=401,
                content={
                    "detail": {
                        "code": "authentication_required",
                        "message": "Invalid password.",
                    }
                },
            )

        credential = next(item for item in config.credentials if item.user == authenticated_user.user)
        response = JSONResponse({"ok": True, "redirect_to": next_path})
        response.set_cookie(
            key=config.session_cookie_name,
            value=_cookie_token_for_credential(credential),
            httponly=True,
            samesite="lax",
        )
        logger.info("Established browser access session user={} next={}", authenticated_user.user, next_path)
        return response

    @app.post("/auth/logout")
    async def access_logout() -> JSONResponse:
        """处理用户登出请求。

        用途:
            清除响应中的 Session Cookie，从而断开用户会话。

        用法:
            客户端 POST 发送请求到 `/auth/logout`。

        @Author: mosliu
        """
        response = JSONResponse({"ok": True})
        response.delete_cookie(config.session_cookie_name)
        return response

    @app.middleware("http")
    async def access_control_middleware(request: Request, call_next):
        """全局 HTTP 访问控制拦截中间件。

        用途:
            拦截除登录登出以外的所有 HTTP 请求，提取并验证用户凭证，拒绝未授权请求，并在请求的 `state` 中注入已通过验证的用户名称。

        @Author: mosliu
        """
        if request.url.path in {"/auth/login", "/auth/logout"}:
            return await call_next(request)

        authenticated_user = _resolve_authenticated_user(config, request)
        if authenticated_user is None:
            logger.warning("Rejected HTTP request method={} path={} from unauthenticated client", request.method, request.url.path)
            return _unauthorized_response(config, request)

        request.state.authenticated_user = authenticated_user.user
        request.state.authenticated_password_source = authenticated_user.password_source

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "HTTP request failed after authentication user={} source={} method={} path={}",
                authenticated_user.user,
                authenticated_user.password_source,
                request.method,
                request.url.path,
            )
            raise

        logger.info(
            "HTTP request user={} source={} method={} path={} status={}",
            authenticated_user.user,
            authenticated_user.password_source,
            request.method,
            request.url.path,
            response.status_code,
        )
        return response
