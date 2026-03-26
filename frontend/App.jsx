/**
 * AXIOM-60 Frontend — Base44 / React component
 *
 * Paste this JSX into your Base44 app (or drop it into a Create React App /
 * Vite project).  Set the two environment variables:
 *
 *   REACT_APP_AXIOM_API_URL  — e.g. https://your-app.up.railway.app
 *   REACT_APP_AXIOM_API_KEY  — your AXIOM_API_KEY value
 *
 * The component renders a form for a single matchup, calls /classify, and
 * displays the result with colour-coded styling that matches the AXIOM-60
 * spec (Green = BET, Purple = LIVE DOG, Orange = PASS filter, Grey = PASS).
 */

import { useState } from "react";

const API_URL = process.env.REACT_APP_AXIOM_API_URL || "";
const API_KEY = process.env.REACT_APP_AXIOM_API_KEY || "";

const SIGNAL_STYLES = {
  BET: { background: "#d4edda", color: "#155724", fontWeight: "bold" },
  PASS: { background: "#e2e3e5", color: "#383d41" },
};

const REASON_STYLES = {
  Edge: SIGNAL_STYLES.BET,
  "LIVE DOG": { background: "#e8d5f5", color: "#6a0dad", fontWeight: "bold" },
  Tempo: { background: "#ffecd2", color: "#7d4e00" },
  SpreadCap: { background: "#ffecd2", color: "#7d4e00" },
  Standard: SIGNAL_STYLES.PASS,
};

function Field({ label, name, value, onChange }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "block", fontFamily: "Arial", marginBottom: 4 }}>
        {label}
      </label>
      <input
        type="number"
        step="0.1"
        name={name}
        value={value}
        onChange={onChange}
        style={{
          fontFamily: "Arial",
          padding: "6px 10px",
          border: "1px solid #ccc",
          borderRadius: 4,
          width: 160,
        }}
      />
    </div>
  );
}

export default function Axiom60() {
  const [form, setForm] = useState({
    fav_adj_em: "",
    dog_adj_em: "",
    spread: "",
    ou: "",
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    try {
      const resp = await fetch(`${API_URL}/classify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY,
        },
        body: JSON.stringify({
          fav_adj_em: parseFloat(form.fav_adj_em),
          dog_adj_em: parseFloat(form.dog_adj_em),
          spread: parseFloat(form.spread),
          ou: parseFloat(form.ou),
        }),
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`${resp.status}: ${text}`);
      }

      setResult(await resp.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const signalStyle = result
    ? REASON_STYLES[result.reason] || SIGNAL_STYLES[result.signal]
    : {};

  return (
    <div style={{ fontFamily: "Arial", maxWidth: 480, margin: "0 auto", padding: 24 }}>
      <h2 style={{ background: "navy", color: "white", padding: "10px 16px", margin: 0 }}>
        AXIOM-60
      </h2>

      <form onSubmit={handleSubmit} style={{ padding: "20px 0" }}>
        <Field label="Fav AdjEM" name="fav_adj_em" value={form.fav_adj_em} onChange={handleChange} />
        <Field label="Dog AdjEM" name="dog_adj_em" value={form.dog_adj_em} onChange={handleChange} />
        <Field label="Spread" name="spread" value={form.spread} onChange={handleChange} />
        <Field label="O/U" name="ou" value={form.ou} onChange={handleChange} />

        <button
          type="submit"
          disabled={loading}
          style={{
            background: "navy",
            color: "white",
            border: "none",
            padding: "8px 20px",
            fontFamily: "Arial",
            cursor: loading ? "not-allowed" : "pointer",
            borderRadius: 4,
          }}
        >
          {loading ? "Classifying…" : "Classify"}
        </button>
      </form>

      {error && (
        <div style={{ color: "#721c24", background: "#f8d7da", padding: 12, borderRadius: 4 }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{ padding: 16, borderRadius: 4, ...signalStyle }}>
          <div style={{ fontSize: 22, marginBottom: 8 }}>
            {result.signal} — {result.reason}
          </div>
          <table style={{ width: "100%", fontFamily: "Arial", borderCollapse: "collapse" }}>
            <tbody>
              {[
                ["BA_Gap", result.ba_gap],
                ["Abs_Edge", result.abs_edge],
                ["Spread", result.spread],
                ["O/U", result.ou],
              ].map(([label, value]) => (
                <tr key={label}>
                  <td style={{ padding: "4px 0", fontWeight: "bold" }}>{label}</td>
                  <td style={{ padding: "4px 0" }}>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
