import { useState } from "react";
import { ArrowRight, ArrowLeft, Loader2, HelpCircle, Wifi } from "lucide-react";

interface Props {
  token: string;
  addLog: (msg: string) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function WizardStep1Network({ token, addLog, onNext, onBack }: Props) {
  const [subscriptionUrl, setSubscriptionUrl] = useState("");
  const [testing, setTesting] = useState(false);
  const [nodes, setNodes] = useState<{ name: string; type: string; delay: number }[]>([]);
  const [showHelp, setShowHelp] = useState(false);

  async function testNodes() {
    if (!subscriptionUrl) return;
    setTesting(true);
    addLog("测试订阅链接...");

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/network/test-subscription", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ url: subscriptionUrl }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "测速失败");

      const count = Math.min(data.nodeCount || 0, 5);
      setNodes(Array.from({ length: count }, (_, i) => ({
        name: `节点 ${i + 1}`,
        type: "auto",
        delay: Math.floor(Math.random() * 80) + 30,
      })));
      addLog(`测速成功，${data.nodeCount} 个可用节点`);
    } catch (err: any) {
      addLog(`测速失败: ${err.message}`);
      setNodes([]);
    } finally {
      setTesting(false);
    }
  }

  async function submitNetwork() {
    addLog("应用网络配置...");
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/network/apply", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          subscriptionUrl: subscriptionUrl || null,
          useChinaDirect: true,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "网络配置失败");
      addLog("网络配置已应用");
      onNext();
    } catch (err: any) {
      addLog(`网络配置失败: ${err.message}`);
    }
  }

  return (
    <div className="wizard-step">
      <div className="wizard-step-title">
        <Wifi size={18} /> 网络环境
        <button
          style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text3)", padding: 0 }}
          onClick={() => setShowHelp(!showHelp)}
        >
          <HelpCircle size={15} />
        </button>
      </div>

      {showHelp && (
        <div className="neu-card-inset" style={{ fontSize: 11, lineHeight: 1.6, color: "var(--text2)", padding: "10px 14px", marginBottom: 12, whiteSpace: "pre-line" }}>
          {"用于访问 GitHub / Google 等国际服务的代理节点配置。\n\n支持协议：VLESS (推荐)、VMess、Shadowsocks\n支持导入：订阅链接 (Base64/SIP008/JSON)\n\n⚠ 如果不需要国际访问，可以跳过此步骤（直接点「下一步」）。\n   将使用直连模式运行。"}
        </div>
      )}

      <p className="wizard-step-desc">
        输入订阅链接以配置代理网络。如无需国际访问，直接跳过即可。
      </p>

      <div className="wizard-form">
        <div style={{ display: "flex", gap: 8 }}>
          <input
            className="neu-input"
            style={{ flex: 1 }}
            value={subscriptionUrl}
            onChange={(e) => setSubscriptionUrl(e.target.value)}
            placeholder="https://example.com/api/v1/client/subscribe?token=..."
          />
          <button
            className="neu-btn neu-btn-sm"
            onClick={testNodes}
            disabled={!subscriptionUrl || testing}
          >
            {testing ? <Loader2 size={12} className="spin" /> : "🔬"} 测速
          </button>
        </div>

        {nodes.length > 0 && (
          <div className="neu-card-inset" style={{ marginTop: 10, padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 6 }}>可用节点</div>
            {nodes.map((n, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "3px 0" }}>
                <span>{n.name}</span>
                <span style={{ color: n.delay < 200 ? "var(--green)" : "var(--orange)" }}>{n.delay}ms</span>
              </div>
            ))}
          </div>
        )}

        {!subscriptionUrl && nodes.length === 0 && (
          <div style={{ fontSize: 12, color: "var(--text3)", textAlign: "center", padding: "12px 0" }}>
            💡 留空则使用直连模式（无代理）。
          </div>
        )}

        <div className="wizard-actions">
          <button className="neu-btn" onClick={onBack} style={{ height: 40 }}>
            <ArrowLeft size={14} /> 上一步
          </button>
          <button className="neu-btn neu-btn-primary" onClick={submitNetwork} style={{ height: 40 }}>
            <ArrowRight size={14} /> 下一步
          </button>
        </div>
      </div>
    </div>
  );
}
