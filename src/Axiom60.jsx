import { useState, useCallback, useRef } from "react";

// ============================================================
//  AXIOM-60  —  Quantitative Margin-Volatility Engine
//  Production Dashboard  •  Local + API Dual Mode
// ============================================================

// — AXIOM-60 CORE ENGINE (runs in-browser, zero dependencies) —
function axiomClassify(favEM, dogEM, spread, ou) {
  const baGap = +(favEM - dogEM).toFixed(4);
  const absEdge = +Math.abs(baGap - Math.abs(spread)).toFixed(4);
  const absSpread = Math.abs(spread);
  let signal, reason;
  if (ou > 148)                                   { signal = "PASS"; reason = "Tempo"; }
  else if (absSpread > 24.5)                      { signal = "PASS"; reason = "SpreadCap"; }
  else if (absEdge >= 1.5)                        { signal = "BET";  reason = "Edge"; }
  else if (absEdge >= 1.0 && baGap < absSpread)   { signal = "BET";  reason = "LIVE DOG"; }
  else                                            { signal = "PASS"; reason = "Standard"; }
  return { signal, reason, ba_gap: baGap, abs_edge: absEdge, spread, ou };
}

// — SIGNAL THEME —
const SIG = {
  BET:       { bg: "#071a0e", bdr: "#00e560", tx: "#00e560", glow: "0 0 24px #00e56033" },
  LIVEDOG:   { bg: "#180d2e", bdr: "#b44dff", tx: "#b44dff", glow: "0 0 24px #b44dff33" },
  Tempo:     { bg: "#1f1400", bdr: "#f0a000", tx: "#f0a000", glow: "none" },
  SpreadCap: { bg: "#1f1400", bdr: "#f0a000", tx: "#f0a000", glow: "none" },
  Standard:  { bg: "#111119", bdr: "#2e2e42", tx: "#5e5e78", glow: "none" },
};

function sigTheme(s, r) {
  if (s === "BET" && r === "LIVE DOG") return SIG.LIVEDOG;
  if (s === "BET") return SIG.BET;
  return SIG[r] || SIG.Standard;
}

// — SEED DATA —
let _nextId = 1;
const seed = () => [
  { id: _nextId++, fav: "Duke",      dog: "Houston",    favEM: 28.5, dogEM: 22.1, spread: -5.5,  ou: 141.0 },
  { id: _nextId++, fav: "Auburn",    dog: "Iowa St",    favEM: 26.8, dogEM: 20.3, spread: -7.0,  ou: 138.5 },
  { id: _nextId++, fav: "Florida",   dog: "Marquette",  favEM: 24.2, dogEM: 21.8, spread: -3.0,  ou: 149.0 },
  { id: _nextId++, fav: "Gonzaga",   dog: "Clemson",    favEM: 27.0, dogEM: 18.5, spread: -9.5,  ou: 152.0 },
  { id: _nextId++, fav: "Tennessee", dog: "Arkansas",   favEM: 25.1, dogEM: 19.6, spread: -4.5,  ou: 133.0 },
  { id: _nextId++, fav: "Kentucky",  dog: "Oregon",     favEM: 23.0, dogEM: 19.0, spread: -4.0,  ou: 140.5 },
  { id: _nextId++, fav: "UConn",     dog: "Michigan St", favEM: 30.2, dogEM: 4.0,  spread: -25.5, ou: 137.0 },
  { id: _nextId++, fav: "Purdue",    dog: "St. John's", favEM: 22.0, dogEM: 18.5, spread: -3.5,  ou: 145.0 },
];

// — TINY COMPONENTS —

function Badge({ signal, reason }) {
  const t = sigTheme(signal, reason);
  const label = signal === "BET" && reason === "LIVE DOG" ? "LIVE DOG" : signal;
  return (
    <span style={{
      background: t.bg,
      border: `1.5px solid ${t.bdr}`,
      color: t.tx,
      boxShadow: t.glow,
      borderRadius: 6,
      padding: "2px 10px",
      fontWeight: 700,
      letterSpacing: 1,
      fontSize: 13,
      whiteSpace: "nowrap",
    }}>{label}</span>
  );
}

function Metric({ v, label, bright }) {
  return (
    <span style={{ display: "inline-flex", flexDirection: "column", alignItems: "center", minWidth: 52 }}>
      <span style={{ color: bright ? "#e8e8ff" : "#9090b0", fontWeight: bright ? 700 : 400, fontSize: 14 }}>
        {typeof v === "number" ? v.toFixed(2) : v}
      </span>
      <span style={{ color: "#44445a", fontSize: 10, letterSpacing: 0.5, marginTop: 1 }}>{label}</span>
    </span>
  );
}

function Stat({ n, label, color }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", minWidth: 60 }}>
      <div style={{ color: color || "#e8e8ff", fontSize: 28, fontWeight: 700, lineHeight: 1 }}>{n}</div>
      <div style={{ color: "#5e5e78", fontSize: 11, marginTop: 4, letterSpacing: 0.5 }}>{label}</div>
    </div>
  );
}

// — SHARED INPUT STYLE —
const inputSx = {
  background: "#16161f",
  border: "1px solid #2e2e42",
  color: "#c8c8e0",
  borderRadius: 4,
  padding: "3px 6px",
  fontSize: 13,
  width: "100%",
  outline: "none",
};

// — MAIN APP —
export default function Axiom60() {
  const [rows, setRows]       = useState(seed);
  const [results, setResults] = useState([]);
  const [mode, setMode]       = useState("local");
  const [apiUrl, setApiUrl]   = useState("");
  const [apiKey, setApiKey]   = useState("");
  const [showCfg, setShowCfg] = useState(false);
  const [busy, setBusy]       = useState(false);
  const [err, setErr]         = useState("");
  const [ran, setRan]         = useState(false);
  const tableRef              = useRef(null);

  // field updater
  const upd = (id, k, v) =>
    setRows(p => p.map(r => r.id === id ? { ...r, [k]: v } : r));

  const addRow = () =>
    setRows(p => [...p, { id: _nextId++, fav: "", dog: "", favEM: 0, dogEM: 0, spread: 0, ou: 140 }]);

  const delRow = id => {
    setRows(p => p.filter(r => r.id !== id));
    setResults(p => p.filter(r => r._id !== id));
  };

  // run engine
  const run = useCallback(async () => {
    if (!rows.length) return;
    setBusy(true); setErr("");
    try {
      if (mode === "local") {
        const res = rows.map(r => ({
          _id: r.id, fav: r.fav, dog: r.dog,
          ...axiomClassify(r.favEM, r.dogEM, r.spread, r.ou),
        }));
        setResults(res);
      } else {
        if (!apiUrl) throw new Error("API URL is required");
        const resp = await fetch(`${apiUrl.replace(/\/+$/, "")}/classify/batch`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "x-api-key": apiKey },
          body: JSON.stringify({
            matchups: rows.map(r => ({
              fav_adj_em: r.favEM, dog_adj_em: r.dogEM, spread: r.spread, ou: r.ou,
            })),
          }),
        });
        if (!resp.ok) {
          const body = await resp.text();
          throw new Error(`API ${resp.status}: ${body.slice(0, 120)}${body.length > 120 ? "…" : ""}`);
        }
        const data = await resp.json();
        const res = data.results.map((d, i) => ({
          _id: rows[i].id, fav: rows[i].fav, dog: rows[i].dog, ...d,
        }));
        setResults(res);
      }
      setRan(true);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }, [rows, mode, apiUrl, apiKey]);

  // summary
  const sm = {
    total: results.length,
    bet:   results.filter(r => r.signal === "BET" && r.reason === "Edge").length,
    dog:   results.filter(r => r.reason === "LIVE DOG").length,
    pass:  results.filter(r => r.signal === "PASS").length,
  };

  // result lookup by row id
  const resultMap = Object.fromEntries(results.map(r => [r._id, r]));

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0b0b12",
      color: "#c8c8e0",
      fontFamily: "Arial, sans-serif",
      padding: "28px 16px",
    }}>

      {/* — HEADER — */}
      <div style={{ maxWidth: 900, margin: "0 auto 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ fontSize: 11, letterSpacing: 2, color: "#5e5e78", textTransform: "uppercase", marginBottom: 4 }}>
              Quantitative Margin-Volatility Engine
            </div>
            <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, color: "#e8e8ff", letterSpacing: 1 }}>
              AXIOM<span style={{ color: "#00e560" }}>-60</span>
            </h1>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setShowCfg(v => !v)}
              style={{
                background: showCfg ? "#1a1a2e" : "transparent",
                border: "1px solid #2e2e42",
                color: "#9090b0",
                borderRadius: 6,
                padding: "6px 14px",
                cursor: "pointer",
                fontSize: 12,
              }}
            >⚙ Config</button>
            <button
              onClick={run}
              disabled={busy || !rows.length}
              style={{
                background: busy ? "#071a0e" : "#00e560",
                color: busy ? "#00e560" : "#071a0e",
                border: "none",
                borderRadius: 6,
                padding: "6px 20px",
                fontWeight: 700,
                fontSize: 13,
                cursor: busy ? "wait" : "pointer",
                opacity: !rows.length ? 0.4 : 1,
                letterSpacing: 0.5,
              }}
            >{busy ? "Running…" : "▶ Run Engine"}</button>
          </div>
        </div>

        {/* — MODE TOGGLE — */}
        <div style={{ marginTop: 14, display: "flex", gap: 6 }}>
          {["local", "api"].map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              style={{
                background: mode === m ? "#1a1a2e" : "transparent",
                border: `1px solid ${mode === m ? "#5050c0" : "#2e2e42"}`,
                color: mode === m ? "#a0a0ff" : "#5e5e78",
                borderRadius: 5,
                padding: "3px 12px",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: mode === m ? 700 : 400,
              }}
            >{m === "local" ? "Local Engine" : "API Mode"}</button>
          ))}
        </div>
      </div>

      <div style={{ maxWidth: 900, margin: "0 auto" }}>

        {/* — CONFIG PANEL — */}
        {showCfg && (
          <div style={{
            background: "#111119",
            border: "1px solid #2e2e42",
            borderRadius: 8,
            padding: "16px 20px",
            marginBottom: 20,
          }}>
            <div style={{ fontSize: 11, letterSpacing: 1, color: "#5e5e78", marginBottom: 12, textTransform: "uppercase" }}>
              API Configuration
            </div>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <div style={{ flex: 2, minWidth: 200 }}>
                <label style={{ fontSize: 11, color: "#5e5e78", display: "block", marginBottom: 4 }}>API URL</label>
                <input
                  style={inputSx}
                  placeholder="https://your-api.example.com"
                  value={apiUrl}
                  onChange={e => setApiUrl(e.target.value)}
                />
              </div>
              <div style={{ flex: 1, minWidth: 140 }}>
                <label style={{ fontSize: 11, color: "#5e5e78", display: "block", marginBottom: 4 }}>API Key</label>
                <input
                  style={inputSx}
                  type="password"
                  placeholder="x-api-key"
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        {/* — ERROR — */}
        {err && (
          <div style={{
            background: "#1f0808",
            border: "1px solid #c03030",
            color: "#ff7070",
            borderRadius: 6,
            padding: "10px 16px",
            marginBottom: 16,
            fontSize: 13,
          }}>⚠ {err}</div>
        )}

        {/* — SUMMARY BAR — */}
        {ran && (
          <div style={{
            background: "#111119",
            border: "1px solid #2e2e42",
            borderRadius: 8,
            padding: "14px 24px",
            marginBottom: 20,
            display: "flex",
            gap: 32,
            alignItems: "center",
            flexWrap: "wrap",
          }}>
            <Stat n={sm.total}  label="Total"     color="#9090b0" />
            <Stat n={sm.bet}    label="BET Edge"  color="#00e560" />
            <Stat n={sm.dog}    label="Live Dog"  color="#b44dff" />
            <Stat n={sm.pass}   label="Pass"      color="#f0a000" />
          </div>
        )}

        {/* — INPUT TABLE — */}
        <div style={{
          background: "#111119",
          border: "1px solid #2e2e42",
          borderRadius: 8,
          overflow: "hidden",
          marginBottom: 20,
        }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "10px 16px",
            borderBottom: "1px solid #2e2e42",
          }}>
            <span style={{ fontSize: 11, letterSpacing: 1, color: "#5e5e78", textTransform: "uppercase" }}>
              Matchup Input
            </span>
            <button
              onClick={addRow}
              style={{
                background: "transparent",
                border: "1px solid #2e2e42",
                color: "#9090b0",
                borderRadius: 5,
                padding: "2px 10px",
                cursor: "pointer",
                fontSize: 12,
              }}
            >+ Add Row</button>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table ref={tableRef} style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#0d0d18" }}>
                  {["Favorite", "Underdog", "Fav EM", "Dog EM", "Spread", "O/U", ""].map(h => (
                    <th key={h} style={{
                      padding: "8px 10px",
                      textAlign: "left",
                      color: "#5e5e78",
                      fontWeight: 600,
                      fontSize: 11,
                      letterSpacing: 0.5,
                      borderBottom: "1px solid #2e2e42",
                      whiteSpace: "nowrap",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const res = resultMap[r.id];
                  const rowBg = res ? sigTheme(res.signal, res.reason).bg : (i % 2 === 0 ? "#111119" : "#0f0f17");
                  return (
                    <tr key={r.id} style={{ background: rowBg, transition: "background 0.2s" }}>
                      {[
                        { k: "fav",    type: "text",   v: r.fav },
                        { k: "dog",    type: "text",   v: r.dog },
                        { k: "favEM",  type: "number", v: r.favEM },
                        { k: "dogEM",  type: "number", v: r.dogEM },
                        { k: "spread", type: "number", v: r.spread },
                        { k: "ou",     type: "number", v: r.ou },
                      ].map(({ k, type, v }) => (
                        <td key={k} style={{ padding: "5px 8px" }}>
                          <input
                            style={inputSx}
                            type={type}
                            step={type === "number" ? "0.1" : undefined}
                            value={v}
                            onChange={e => upd(r.id, k, type === "number" ? parseFloat(e.target.value) || 0 : e.target.value)}
                          />
                        </td>
                      ))}
                      <td style={{ padding: "5px 8px", whiteSpace: "nowrap" }}>
                        <button
                          onClick={() => delRow(r.id)}
                          title="Remove row"
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "#3e3e52",
                            cursor: "pointer",
                            fontSize: 15,
                            padding: "2px 4px",
                          }}
                        >✕</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* — RESULTS TABLE — */}
        {ran && results.length > 0 && (
          <div style={{
            background: "#111119",
            border: "1px solid #2e2e42",
            borderRadius: 8,
            overflow: "hidden",
          }}>
            <div style={{ padding: "10px 16px", borderBottom: "1px solid #2e2e42" }}>
              <span style={{ fontSize: 11, letterSpacing: 1, color: "#5e5e78", textTransform: "uppercase" }}>
                Signal Output
              </span>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#0d0d18" }}>
                    {["Matchup", "Signal", "Reason", "BA Gap", "Abs Edge", "Spread", "O/U"].map(h => (
                      <th key={h} style={{
                        padding: "8px 12px",
                        textAlign: "left",
                        color: "#5e5e78",
                        fontWeight: 600,
                        fontSize: 11,
                        letterSpacing: 0.5,
                        borderBottom: "1px solid #2e2e42",
                        whiteSpace: "nowrap",
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => {
                    const t = sigTheme(r.signal, r.reason);
                    return (
                      <tr
                        key={r._id}
                        style={{
                          background: i % 2 === 0 ? t.bg : `${t.bg}cc`,
                          borderLeft: `3px solid ${t.bdr}`,
                        }}
                      >
                        <td style={{ padding: "8px 12px", color: "#c8c8e0", whiteSpace: "nowrap" }}>
                          <span style={{ color: "#e8e8ff", fontWeight: 600 }}>{r.fav}</span>
                          <span style={{ color: "#44445a", margin: "0 6px" }}>vs</span>
                          <span style={{ color: "#9090b0" }}>{r.dog}</span>
                        </td>
                        <td style={{ padding: "8px 12px" }}>
                          <Badge signal={r.signal} reason={r.reason} />
                        </td>
                        <td style={{ padding: "8px 12px", color: t.tx, fontSize: 12 }}>{r.reason}</td>
                        <td style={{ padding: "8px 12px" }}>
                          <Metric v={r.ba_gap} label="BA Gap" bright={r.signal === "BET"} />
                        </td>
                        <td style={{ padding: "8px 12px" }}>
                          <Metric v={r.abs_edge} label="Abs Edge" bright={r.signal === "BET"} />
                        </td>
                        <td style={{ padding: "8px 12px", color: "#9090b0" }}>{r.spread}</td>
                        <td style={{ padding: "8px 12px", color: "#9090b0" }}>{r.ou}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* — EMPTY STATE — */}
        {!ran && (
          <div style={{
            textAlign: "center",
            padding: "40px 0",
            color: "#3e3e52",
            fontSize: 13,
            letterSpacing: 0.5,
          }}>
            Enter matchup data above and click <strong style={{ color: "#5e5e78" }}>▶ Run Engine</strong> to classify.
          </div>
        )}
      </div>
    </div>
  );
}
