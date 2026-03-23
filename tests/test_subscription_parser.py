# tests/test_subscription_parser.py — Task 2.1 验收测试
# 3 个验收场景：Clash YAML / Base64 V2Ray / 兜底节点 VLESS URI

import base64
import json
import os
import sys
import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.subscription_parser import SubscriptionParser, ParsedNode
from backend.services.singbox_manager import parse_vless_uri, get_fallback_outbound


# ── 测试数据 ────────────────────────────────────────────

CLASH_YAML = """
proxies:
  - name: "HK-SS-01"
    type: ss
    server: hk1.example.com
    port: 8388
    cipher: aes-256-gcm
    password: "test-password-123"
  - name: "JP-VMess-01"
    type: vmess
    server: jp1.example.com
    port: 443
    uuid: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    alterId: 0
    cipher: auto
  - name: "US-VLESS-01"
    type: vless
    server: us1.example.com
    port: 443
    uuid: "11111111-2222-3333-4444-555555555555"
    flow: xtls-rprx-vision
"""

VMESS_URI_JSON = json.dumps({
    "v": "2",
    "ps": "Tokyo-Fast",
    "add": "tokyo.example.com",
    "port": "443",
    "id": "test-uuid-vmess-001",
    "aid": "0",
    "scy": "auto",
    "net": "ws",
    "path": "/vmess-ws",
    "host": "cdn.example.com",
    "tls": "tls",
    "sni": "cdn.example.com",
})

BASE64_V2RAY_CONTENT = base64.b64encode(
    f"vmess://{base64.b64encode(VMESS_URI_JSON.encode()).decode()}\n"
    f"vless://test-uuid-vless@sg1.example.com:2053"
    f"?encryption=none&security=tls&type=ws&path=%2Fvless-ws"
    f"&sni=sg1.example.com&fp=chrome#Singapore\n".encode()
).decode()

FALLBACK_VLESS_URI = (
    "vless://b32fc64c-8b6e-4fe7-9710-ab181cbc550f@23.27.134.79:48782"
    "?encryption=none&security=reality&flow=&type=h2"
    "&sni=dash.cloudflare.com"
    "&pbk=RokFzFe0TXFXNr-mdGGf2QNEebOKBrw-IwfLOEw6yn8"
    "&fp=chrome#USA"
)


# ── 验收场景 1：Clash YAML 订阅 ────────────────────────

class TestClashYAML:
    """传入 Clash YAML 订阅，输出含正确 tag 的 ParsedNode 列表"""

    def test_parse_clash_yaml_nodes(self):
        parser = SubscriptionParser()
        nodes = parser._detect_and_parse(CLASH_YAML, "text/yaml")

        assert len(nodes) == 3

        # SS 节点
        ss = nodes[0]
        assert ss.tag == "HK-SS-01"
        assert ss.protocol == "ss"
        assert ss.address == "hk1.example.com"
        assert ss.port == 8388
        assert ss.raw_outbound["type"] == "shadowsocks"
        assert ss.raw_outbound["method"] == "aes-256-gcm"
        assert ss.raw_outbound["password"] == "test-password-123"

        # VMess 节点
        vmess = nodes[1]
        assert vmess.tag == "JP-VMess-01"
        assert vmess.protocol == "vmess"
        assert vmess.raw_outbound["uuid"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

        # VLESS 节点
        vless = nodes[2]
        assert vless.tag == "US-VLESS-01"
        assert vless.protocol == "vless"
        assert vless.raw_outbound["flow"] == "xtls-rprx-vision"

    def test_clash_yaml_content_type_detection(self):
        """content-type 含 yaml 时正确识别为 Clash 格式"""
        parser = SubscriptionParser()
        nodes = parser._detect_and_parse(CLASH_YAML, "application/x-yaml; charset=utf-8")
        assert len(nodes) == 3

    def test_clash_yaml_prefix_detection(self):
        """首行含 proxies: 时也能正确识别"""
        parser = SubscriptionParser()
        nodes = parser._detect_and_parse(CLASH_YAML, "text/plain")
        # 内容以 \nproxies: 开始（strip 后），应被嗅探为 Clash YAML
        # 注意：CLASH_YAML 首行是空行，strip 后以 proxies: 开头
        assert len(nodes) == 3


# ── 验收场景 2：Base64 V2Ray URI 列表 ──────────────────

class TestBase64V2Ray:
    """传入 Base64 V2Ray URI 列表，正确解析 vmess 节点"""

    def test_parse_base64_vmess_node(self):
        parser = SubscriptionParser()
        nodes = parser._detect_and_parse(BASE64_V2RAY_CONTENT, "text/plain")

        assert len(nodes) == 2

        # VMess 节点
        vmess = nodes[0]
        assert vmess.tag == "Tokyo-Fast"
        assert vmess.protocol == "vmess"
        assert vmess.address == "tokyo.example.com"
        assert vmess.port == 443
        assert vmess.raw_outbound["uuid"] == "test-uuid-vmess-001"
        assert vmess.raw_outbound["transport"]["type"] == "websocket"
        assert vmess.raw_outbound["transport"]["path"] == "/vmess-ws"
        assert vmess.raw_outbound["tls"]["enabled"] is True

        # VLESS 节点
        vless = nodes[1]
        assert vless.tag == "Singapore"
        assert vless.protocol == "vless"
        assert vless.address == "sg1.example.com"
        assert vless.port == 2053


# ── 验收场景 3：兜底节点 VLESS URI ─────────────────────

class TestFallbackVLESS:
    """SINGBOX_FALLBACK_URI 设为 VLESS URI，get_fallback_outbound() 返回正确字典"""

    def test_parse_vless_uri_fields(self):
        """parse_vless_uri 正确解析所有字段"""
        outbound = parse_vless_uri(FALLBACK_VLESS_URI)

        assert outbound["type"] == "vless"
        assert outbound["tag"] == "USA"
        assert outbound["server"] == "23.27.134.79"
        assert outbound["server_port"] == 48782
        assert outbound["uuid"] == "b32fc64c-8b6e-4fe7-9710-ab181cbc550f"

        # REALITY TLS
        assert outbound["tls"]["enabled"] is True
        assert outbound["tls"]["server_name"] == "dash.cloudflare.com"
        assert outbound["tls"]["utls"]["fingerprint"] == "chrome"
        assert outbound["tls"]["reality"]["enabled"] is True
        assert outbound["tls"]["reality"]["public_key"] == "RokFzFe0TXFXNr-mdGGf2QNEebOKBrw-IwfLOEw6yn8"

        # H2 传输层
        assert outbound["transport"]["type"] == "http"

    def test_parse_vless_uri_invalid_scheme(self):
        """非 vless:// scheme 抛出 ValueError"""
        with pytest.raises(ValueError, match="仅支持 vless://"):
            parse_vless_uri("vmess://invalid@host:443")

    def test_get_fallback_outbound(self, monkeypatch):
        """get_fallback_outbound() 从环境变量读取并正确解析"""
        monkeypatch.setattr(
            "backend.services.singbox_manager.settings",
            type("MockSettings", (), {"singbox_fallback_uri": FALLBACK_VLESS_URI})(),
        )
        outbound = get_fallback_outbound()
        assert outbound["server"] == "23.27.134.79"
        assert outbound["uuid"] == "b32fc64c-8b6e-4fe7-9710-ab181cbc550f"
        assert outbound["tls"]["reality"]["public_key"] == "RokFzFe0TXFXNr-mdGGf2QNEebOKBrw-IwfLOEw6yn8"

    def test_get_fallback_outbound_empty_uri(self, monkeypatch):
        """SINGBOX_FALLBACK_URI 为空时抛出 RuntimeError"""
        monkeypatch.setattr(
            "backend.services.singbox_manager.settings",
            type("MockSettings", (), {"singbox_fallback_uri": ""})(),
        )
        with pytest.raises(RuntimeError, match="SINGBOX_FALLBACK_URI 未设置"):
            get_fallback_outbound()
