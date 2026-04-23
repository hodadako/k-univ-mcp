from __future__ import annotations

from dataclasses import dataclass


class YonseiBootstrapError(RuntimeError):
    pass


def parse_cookie_header(cookie_header: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for part in cookie_header.split(";"):
        chunk = part.strip()
        if not chunk or "=" not in chunk:
            continue
        name, value = chunk.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies


@dataclass(slots=True)
class EnvCookieBootstrap:
    cookie_header: str | None

    def resolve_cookie_header(self) -> str:
        if not self.cookie_header:
            raise YonseiBootstrapError(
                "YONSEI_COOKIE is required. Provide a cookie string such as 'JSESSIONID=...' optionally followed by 'NetFunnel_ID=...'."
            )
        cookies = parse_cookie_header(self.cookie_header)
        if "JSESSIONID" not in cookies:
            raise YonseiBootstrapError(
                "YONSEI_COOKIE must include JSESSIONID. NetFunnel_ID is optional because Yonsei may leave it empty while still serving API responses."
            )
        return self.cookie_header
