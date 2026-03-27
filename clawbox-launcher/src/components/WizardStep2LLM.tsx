import { useState } from "react";
import { ArrowRight, ArrowLeft, Loader2, Brain, RefreshCw } from "lucide-react";

interface Props {
  token: string;
  addLog: (msg: string) => void;
  onNext: () => void;
  onBack: () => void;
}

const PROVIDERS = [
  { value: "bailian", label: "阿里云百炼" },
  { value: "deepseek", label: "DeepSeek 官方" },
  { value: "openai", label: "OpenAI API" },
  { value: "anthropic", label: "Anthropic" },
  { value: "gemini", label: "Google Gemini" },
  { value: "custom", label: "自定义 (Custom)" },
];

const PRESET_BASE_URLS: Record<string, string> = {
  bailian: "https://coding.dashscope.aliyuncs.com/v1",
  deepseek: "https://api.deepseek.com",
  openai: "https://api.openai.com/v1",
  anthropic: "https://api.anthropic.com/v1",
  gemini: "https://generativelanguage.googleapis.com/v1beta",
};

const PRESET_MODELS: Record<string, string[]> = {
  bailian: ["qwen3.5-plus", "qwen3-max-2026-01-23", "qwen3-coder-next", "qwen3-coder-plus", "glm-5", "kimi-k2.5"],
};

export default function WizardStep2LLM({ token, addLog, onNext, onBack }: Props) {
  const [provider, setProvider] = useState("bailian");
  const [apiKey, setApiKey] = useState("");
  const [modelName, setModelName] = useState(PRESET_MODELS.bailian?.[0] || "");
  const [customBaseUrl, setCustomBaseUrl] = useState(PRESET_BASE_URLS.bailian || "");
  const [models, setModels] = useState<string[]>(PRESET_MODELS.bailian || []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleProviderChange(val: string) {
    setProvider(val);
    setModelName("");
    setModels([]);
    setError("");
    setCustomBaseUrl(PRESET_BASE_URLS[val] || "");

    if (val === "bailian") {
      const preset = PRESET_MODELS.bailian || [];
      setModels(preset);
      if (preset.length > 0) setModelName(preset[0]);
    }
  }

  async function fetchModels() {
    if (!apiKey) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ provider, api_key: apiKey });
      if (customBaseUrl) params.append("base_url", customBaseUrl);

      const res = await fetch(`http://127.0.0.1:8000/api/v1/llm/models?${params}`, {
        headers: { "Authorization": `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      const list = data.models || [];
      if (list.length > 0) {
        setModels(list);
        setModelName(list[0]);
        addLog(`获取到 ${list.length} 个模型`);
      } else {
        setError("未获取到模型");
      }
    } catch {
      setError("获取模型列表失败，请手动输入");
    } finally {
      setLoading(false);
    }
  }

  async function submitLLM() {
    if (!apiKey) { setError("请输入 API Key"); return; }
    if (!modelName) { setError("请选择或输入模型"); return; }
    if ((provider === "custom" || provider === "bailian") && !customBaseUrl) {
      setError("请输入 Base URL"); return;
    }

    addLog("应用 LLM 配置...");
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/llm/apply", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          provider,
          model_name: modelName,
          api_key: apiKey,
          custom_base_url: customBaseUrl,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "配置失败");
      addLog("LLM 配置已应用");
      onNext();
    } catch (err: any) {
      setError(err.message);
      addLog(`LLM 配置失败: ${err.message}`);
    }
  }

  const showBaseUrl = provider === "bailian" || provider === "custom";
  const showFetchBtn = provider !== "bailian" && provider !== "custom";

  return (
    <div className="wizard-step">
      <div className="wizard-step-title"><Brain size={18} /> 大模型接入</div>
      <p className="wizard-step-desc">选择 AI 模型提供商并填入 API Key。</p>

      <div className="wizard-form">
        {/* Provider */}
        <div className="wizard-field">
          <label>提供商</label>
          <select
            className="neu-input"
            value={provider}
            onChange={(e) => handleProviderChange(e.target.value)}
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>

        {/* Base URL (bailian / custom only) */}
        {showBaseUrl && (
          <div className="wizard-field">
            <label>Base URL</label>
            <input
              className="neu-input"
              value={customBaseUrl}
              onChange={(e) => setCustomBaseUrl(e.target.value)}
              placeholder={provider === "bailian"
                ? "https://dashscope.aliyuncs.com/compatible-mode/v1"
                : "https://api.example.com/v1"
              }
            />
            {provider === "bailian" && (
              <div style={{ fontSize: 10, color: "var(--text3)", marginTop: 4 }}>
                标准版: dashscope.aliyuncs.com/compatible-mode/v1 | Coding Plan（默认）: coding.dashscope.aliyuncs.com/v1
              </div>
            )}
          </div>
        )}

        {/* API Key */}
        <div className="wizard-field">
          <label>API Key</label>
          <div style={{ display: "flex", gap: 6 }}>
            <input
              className="neu-input"
              type="password"
              style={{ flex: 1 }}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
            />
            {showFetchBtn && (
              <button
                className="neu-btn neu-btn-sm"
                onClick={fetchModels}
                disabled={!apiKey || loading}
              >
                {loading ? <Loader2 size={12} className="spin" /> : <RefreshCw size={12} />}
                {" "}获取模型
              </button>
            )}
          </div>
        </div>

        {/* Model */}
        <div className="wizard-field">
          <label>驱动模型</label>
          {models.length > 0 ? (
            <select
              className="neu-input"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
            >
              {models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          ) : (
            <input
              className="neu-input"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="手动输入模型 ID"
            />
          )}
        </div>

        {error && <div className="wizard-error">{error}</div>}

        <div className="wizard-actions">
          <button className="neu-btn" onClick={onBack} style={{ height: 40 }}>
            <ArrowLeft size={14} /> 上一步
          </button>
          <button className="neu-btn neu-btn-primary" onClick={submitLLM} style={{ height: 40 }}>
            <ArrowRight size={14} /> 下一步
          </button>
        </div>
      </div>
    </div>
  );
}
