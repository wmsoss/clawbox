# backend/services/subscription_parser.py — 机场订阅解析器 (多格式)
# 按白皮书 §5.1 实现：三种格式嗅探 + sing-box outbound 转换

import base64
import json
import yaml
import httpx
from typing import List
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs, unquote


@dataclass
class ParsedNode:
    """解析后的代理节点"""
    tag: str              # 节点名称
    protocol: str         # vless / vmess / ss / trojan
    address: str          # 服务器地址
    port: int             # 端口
    raw_outbound: dict    # 符合 sing-box outbound 格式的完整字典


class SubscriptionParser:
    """
    机场订阅解析器。

    支持三种格式：
    1. Sing-box JSON（响应体含 outbounds 字段）
    2. Clash YAML（Content-Type 含 yaml 或首行含 proxies:）
    3. Base64 编码的 V2Ray URI 列表
    """

    async def fetch_and_parse(self, url: str, proxy: str | None = None) -> List[ParsedNode]:
        """
        主入口。通过可选的 SOCKS5 代理拉取订阅链接并解析。

        Args:
            url: 订阅链接
            proxy: 代理地址，格式 "socks5://127.0.0.1:2080"

        Returns:
            解析后的节点列表
        """
        async with httpx.AsyncClient(proxy=proxy, timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        return self._detect_and_parse(resp.text, resp.headers.get("content-type", ""))

    def _detect_and_parse(self, content: str, content_type: str) -> List[ParsedNode]:
        """格式嗅探 + 分发解析"""
        stripped = content.strip()

        # 1. 尝试 Sing-box JSON
        if stripped.startswith("{"):
            try:
                data = json.loads(stripped)
                if "outbounds" in data:
                    return self._parse_singbox_json(data)
            except json.JSONDecodeError:
                pass

        # 2. 尝试 Clash YAML
        if "yaml" in content_type.lower() or stripped.startswith("proxies:"):
            return self._parse_clash_yaml(content)

        # 3. 尝试 Base64 V2Ray URI 列表
        try:
            # 补全 padding
            padded = content.strip()
            padding = 4 - len(padded) % 4
            if padding != 4:
                padded += "=" * padding
            decoded = base64.b64decode(padded).decode("utf-8")
            lines = [l.strip() for l in decoded.splitlines() if l.strip()]
            if lines and any(
                lines[0].startswith(p)
                for p in ("vmess://", "vless://", "ss://", "trojan://")
            ):
                return self._parse_v2ray_uri_list(decoded)
        except Exception:
            pass

        raise ValueError(f"无法识别订阅格式，content-type={content_type}")

    # ── Sing-box JSON 解析 ──────────────────────────────

    def _parse_singbox_json(self, data: dict) -> List[ParsedNode]:
        """解析 Sing-box JSON 格式，提取有效 outbound"""
        nodes = []
        valid_types = {"vless", "vmess", "shadowsocks", "trojan", "hysteria2", "tuic"}

        for outbound in data.get("outbounds", []):
            ob_type = outbound.get("type", "")
            if ob_type not in valid_types:
                continue

            # shadowsocks → ss for protocol field
            protocol = "ss" if ob_type == "shadowsocks" else ob_type
            nodes.append(ParsedNode(
                tag=outbound.get("tag", f"{protocol}-{len(nodes)}"),
                protocol=protocol,
                address=outbound.get("server", ""),
                port=outbound.get("server_port", 0),
                raw_outbound=outbound,
            ))
        return nodes

    # ── Clash YAML 解析 ─────────────────────────────────

    def _parse_clash_yaml(self, content: str) -> List[ParsedNode]:
        """解析 Clash YAML 格式，转换为 sing-box outbound 字典"""
        data = yaml.safe_load(content)
        nodes = []
        for proxy in data.get("proxies", []):
            outbound = self._clash_proxy_to_singbox_outbound(proxy)
            if outbound:
                nodes.append(ParsedNode(
                    tag=proxy["name"],
                    protocol=proxy["type"],
                    address=proxy["server"],
                    port=proxy["port"],
                    raw_outbound=outbound,
                ))
        return nodes

    def _clash_proxy_to_singbox_outbound(self, proxy: dict) -> dict | None:
        """Clash proxy 字段 → sing-box outbound 格式转换"""
        ptype = proxy.get("type", "").lower()

        if ptype == "ss":
            return {
                "type": "shadowsocks",
                "tag": proxy["name"],
                "server": proxy["server"],
                "server_port": proxy["port"],
                "method": proxy["cipher"],
                "password": proxy["password"],
            }
        elif ptype == "vmess":
            return {
                "type": "vmess",
                "tag": proxy["name"],
                "server": proxy["server"],
                "server_port": proxy["port"],
                "uuid": proxy["uuid"],
                "security": proxy.get("cipher", "auto"),
                "alter_id": proxy.get("alterId", 0),
            }
        elif ptype == "vless":
            return {
                "type": "vless",
                "tag": proxy["name"],
                "server": proxy["server"],
                "server_port": proxy["port"],
                "uuid": proxy["uuid"],
                "flow": proxy.get("flow", ""),
            }
        elif ptype == "trojan":
            outbound = {
                "type": "trojan",
                "tag": proxy["name"],
                "server": proxy["server"],
                "server_port": proxy["port"],
                "password": proxy["password"],
            }
            # TLS 配置
            if proxy.get("sni"):
                outbound["tls"] = {
                    "enabled": True,
                    "server_name": proxy["sni"],
                }
            return outbound

        return None

    # ── Base64 V2Ray URI 解析 ───────────────────────────

    def _parse_v2ray_uri_list(self, decoded_content: str) -> List[ParsedNode]:
        """解析 Base64 解码后的 V2Ray URI 列表"""
        nodes = []
        for line in decoded_content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                node = self._parse_single_uri(line)
                if node:
                    nodes.append(node)
            except Exception:
                # 跳过无法解析的行
                continue
        return nodes

    def _parse_single_uri(self, uri: str) -> ParsedNode | None:
        """解析单行 V2Ray URI"""
        if uri.startswith("vmess://"):
            return self._parse_vmess_uri(uri)
        elif uri.startswith("vless://"):
            return self._parse_vless_uri(uri)
        elif uri.startswith("ss://"):
            return self._parse_ss_uri(uri)
        elif uri.startswith("trojan://"):
            return self._parse_trojan_uri(uri)
        return None

    def _parse_vmess_uri(self, uri: str) -> ParsedNode:
        """
        解析 vmess:// URI (Base64 编码的 JSON)

        格式: vmess://<base64 encoded json>
        JSON 结构: {"v":"2","ps":"name","add":"host","port":"443","id":"uuid",...}
        """
        encoded = uri[len("vmess://"):]
        # 补全 padding
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += "=" * padding
        config = json.loads(base64.b64decode(encoded).decode("utf-8"))

        tag = config.get("ps", "vmess-node")
        host = config.get("add", "")
        port = int(config.get("port", 0))

        outbound = {
            "type": "vmess",
            "tag": tag,
            "server": host,
            "server_port": port,
            "uuid": config.get("id", ""),
            "security": config.get("scy", "auto"),
            "alter_id": int(config.get("aid", 0)),
        }

        # 传输层
        net = config.get("net", "tcp")
        if net == "ws":
            outbound["transport"] = {
                "type": "websocket",
                "path": config.get("path", "/"),
                "headers": {"Host": config.get("host", "")} if config.get("host") else {},
            }
        elif net == "h2":
            outbound["transport"] = {"type": "http"}
        elif net == "grpc":
            outbound["transport"] = {
                "type": "grpc",
                "service_name": config.get("path", ""),
            }

        # TLS
        if config.get("tls") == "tls":
            outbound["tls"] = {
                "enabled": True,
                "server_name": config.get("sni", config.get("host", host)),
            }

        return ParsedNode(tag=tag, protocol="vmess", address=host, port=port, raw_outbound=outbound)

    def _parse_vless_uri(self, uri: str) -> ParsedNode:
        """解析 vless:// URI，复用 singbox_manager.parse_vless_uri"""
        from backend.services.singbox_manager import parse_vless_uri

        outbound = parse_vless_uri(uri)
        return ParsedNode(
            tag=outbound["tag"],
            protocol="vless",
            address=outbound["server"],
            port=outbound["server_port"],
            raw_outbound=outbound,
        )

    def _parse_ss_uri(self, uri: str) -> ParsedNode:
        """
        解析 ss:// URI

        格式: ss://<base64(method:password)>@host:port#tag
        或:   ss://<base64(method:password@host:port)>#tag
        """
        parsed = urlparse(uri)
        tag = unquote(parsed.fragment) if parsed.fragment else "ss-node"

        if parsed.username:
            # 格式: ss://base64(method:password)@host:port#tag
            userinfo = parsed.username
            if parsed.password:
                userinfo += ":" + parsed.password
            # 尝试 base64 解码 userinfo
            try:
                padding = 4 - len(userinfo) % 4
                if padding != 4:
                    userinfo += "=" * padding
                decoded = base64.b64decode(userinfo).decode("utf-8")
                method, password = decoded.split(":", 1)
            except Exception:
                method, password = userinfo, ""
            host = parsed.hostname or ""
            port = parsed.port or 0
        else:
            # 格式: ss://base64(method:password@host:port)#tag
            encoded = uri[len("ss://"):].split("#")[0]
            padding = 4 - len(encoded) % 4
            if padding != 4:
                encoded += "=" * padding
            decoded = base64.b64decode(encoded).decode("utf-8")
            method_pass, host_port = decoded.rsplit("@", 1)
            method, password = method_pass.split(":", 1)
            host, port_str = host_port.rsplit(":", 1)
            port = int(port_str)

        outbound = {
            "type": "shadowsocks",
            "tag": tag,
            "server": host,
            "server_port": port,
            "method": method,
            "password": password,
        }

        return ParsedNode(tag=tag, protocol="ss", address=host, port=port, raw_outbound=outbound)

    def _parse_trojan_uri(self, uri: str) -> ParsedNode:
        """
        解析 trojan:// URI

        格式: trojan://password@host:port?sni=...#tag
        """
        parsed = urlparse(uri)
        tag = unquote(parsed.fragment) if parsed.fragment else "trojan-node"
        password = parsed.username or ""
        host = parsed.hostname or ""
        port = parsed.port or 0
        qs = parse_qs(parsed.query)

        outbound: dict = {
            "type": "trojan",
            "tag": tag,
            "server": host,
            "server_port": port,
            "password": password,
        }

        sni = qs.get("sni", [""])[0]
        if sni:
            outbound["tls"] = {
                "enabled": True,
                "server_name": sni,
            }

        return ParsedNode(tag=tag, protocol="trojan", address=host, port=port, raw_outbound=outbound)

    # ── Config 构建 ─────────────────────────────────────

    def _build_urltest_group(self, nodes: List[ParsedNode], tag: str = "auto") -> dict:
        """构造 urltest 自动优选出站组"""
        return {
            "type": "urltest",
            "tag": tag,
            "outbounds": [n.tag for n in nodes],
            "url": "https://www.gstatic.com/generate_204",
            "interval": "3m",
            "tolerance": 50,
        }

    def _build_urltest_group_from_tags(self, tags: list[str], group_tag: str = "auto") -> dict:
        """从 tag 列表构造 urltest 出站组"""
        return {
            "type": "urltest",
            "tag": group_tag,
            "outbounds": tags,
            "url": "https://www.gstatic.com/generate_204",
            "interval": "3m",
            "tolerance": 50,
        }

    def build_singbox_config(
        self,
        nodes: List[ParsedNode],
        fallback_node: dict,
        dns_china_direct: bool = True,
    ) -> dict:
        """
        组装完整 sing-box config.json

        Args:
            nodes: 解析后的用户节点列表
            fallback_node: 内置兜底 VLESS-REALITY outbound 字典
            dns_china_direct: 是否开启国内 DNS 直连
        """
        all_outbounds = [n.raw_outbound for n in nodes]
        all_outbounds.append(fallback_node)

        # 组合代理 tags：用户节点 + 兜底节点
        proxy_tags = [n.tag for n in nodes] if nodes else [fallback_node["tag"]]
        if fallback_node["tag"] not in proxy_tags:
            proxy_tags.append(fallback_node["tag"])

        urltest_group = self._build_urltest_group_from_tags(proxy_tags)

        return {
            "log": {"level": "warn"},
            "dns": self._build_dns_config(dns_china_direct),
            "inbounds": [
                {"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 2080}
            ],
            "outbounds": [urltest_group, {"type": "direct", "tag": "direct"}] + all_outbounds,
            "route": self._build_route_rules(urltest_group["tag"]),
            "experimental": {"cache_file": {"enabled": True}},
        }

    def _build_dns_config(self, china_direct: bool) -> dict:
        """DNS 分流：国内走 223.5.5.5 直连，海外走 1.1.1.1 通过代理
        sing-box 1.12.0 新格式：使用 type + server 替代 address
        """
        servers = [
            {"type": "udp", "tag": "dns-remote", "server": "1.1.1.1", "detour": "auto"},
            {"type": "udp", "tag": "dns-china", "server": "223.5.5.5"},
        ]
        rules = []
        if china_direct:
            rules.append({"rule_set": "geosite-cn", "server": "dns-china"})
        return {"servers": servers, "rules": rules}

    def _build_route_rules(self, proxy_tag: str) -> dict:
        """路由规则：国内直连，其余走代理
        sing-box 1.8.0+ 格式：使用 rule_set 替代 geosite/geoip
        """
        return {
            "default_domain_resolver": {
                "server": "dns-remote",
            },
            "rules": [
                {"rule_set": ["geosite-cn", "geoip-cn"], "outbound": "direct"},
                {"ip_is_private": True, "outbound": "direct"},
            ],
            "rule_set": [
                {
                    "tag": "geosite-cn",
                    "type": "remote",
                    "format": "binary",
                    "url": "https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-cn.srs",
                    "download_detour": proxy_tag,
                },
                {
                    "tag": "geoip-cn",
                    "type": "remote",
                    "format": "binary",
                    "url": "https://raw.githubusercontent.com/SagerNet/sing-geoip/rule-set/geoip-cn.srs",
                    "download_detour": proxy_tag,
                },
            ],
            "final": proxy_tag,
            "auto_detect_interface": True,
        }
