import { useState } from "react";
import { User, Lock, ArrowRight, Loader2 } from "lucide-react";

interface Props {
  addLog: (msg: string) => void;
  onNext: (token: string) => void;
}

export default function WizardStep0Admin({ addLog, onNext }: Props) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (username.length < 3) { setError("用户名至少 3 个字符"); return; }
    if (password.length < 8) { setError("密码至少 8 个字符"); return; }

    setLoading(true);
    setError("");
    addLog("注册/登录管理员...");

    try {
      // Register (ignores 409 if user exists)
      const regRes = await fetch("http://127.0.0.1:8000/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!regRes.ok && regRes.status !== 409) {
        const err = await regRes.json().catch(() => ({}));
        throw new Error(err.detail || "注册失败");
      }

      // Login
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);
      const loginRes = await fetch("http://127.0.0.1:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: params,
      });
      const loginData = await loginRes.json().catch(() => ({}));
      if (!loginRes.ok) throw new Error(loginData.detail || "登录失败");

      addLog("管理员验证成功");
      onNext(loginData.access_token);
    } catch (err: any) {
      setError(err.message || "操作失败");
      addLog(`管理员验证失败: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="wizard-step">
      <div className="wizard-step-title">👤 管理员设置</div>
      <p className="wizard-step-desc">
        ClawBox 采用单用户管理机制，首次运行需设置管理员账号。
      </p>

      <form onSubmit={handleSubmit} className="wizard-form">
        <div className="wizard-field">
          <label><User size={13} /> 用户名</label>
          <input
            className="neu-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="至少 3 个字符"
          />
        </div>
        <div className="wizard-field">
          <label><Lock size={13} /> 密码</label>
          <input
            className="neu-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="至少 8 个字符"
          />
        </div>

        {error && <div className="wizard-error">{error}</div>}

        <button
          type="submit"
          className="neu-btn neu-btn-primary"
          style={{ width: "100%", height: 44 }}
          disabled={loading}
        >
          {loading ? <Loader2 size={16} className="spin" /> : <ArrowRight size={16} />}
          {loading ? " 验证中..." : " 下一步"}
        </button>
      </form>
    </div>
  );
}
