"""Script to generate animated SVG video walkthrough demonstration."""

from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "assets" / "screenshots"


def generate_animated_walkthrough_svg():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 700" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="brandGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4f46e5"/>
      <stop offset="100%" stop-color="#06b6d4"/>
    </linearGradient>
    <linearGradient id="barGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#ef4444"/>
      <stop offset="100%" stop-color="#f59e0b"/>
    </linearGradient>
    <style>
      @keyframes typeText {
        0% { opacity: 0; }
        20% { opacity: 1; }
        90% { opacity: 1; }
        100% { opacity: 0; }
      }
      @keyframes gaugeMove {
        0% { width: 0px; }
        25% { width: 440px; }
        85% { width: 440px; }
        100% { width: 0px; }
      }
      @keyframes pulseBadge {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
      }
      @keyframes progressBar {
        0% { width: 0px; }
        100% { width: 1120px; }
      }
      .anim-type { animation: typeText 12s infinite; }
      .anim-gauge { animation: gaugeMove 12s infinite ease-out; }
      .anim-badge { animation: pulseBadge 2s infinite ease-in-out; }
      .anim-progress { animation: progressBar 12s linear infinite; }
    </style>
  </defs>

  <rect width="1200" height="700" fill="url(#bgGrad)"/>

  <!-- Window Frame / Video Player Header -->
  <rect x="0" y="0" width="1200" height="42" fill="#090d16" stroke="#1e293b"/>
  <circle cx="25" cy="21" r="6" fill="#ef4444"/>
  <circle cx="45" cy="21" r="6" fill="#f59e0b"/>
  <circle cx="65" cy="21" r="6" fill="#10b981"/>
  <text x="100" y="26" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="12">ICIP Interactive Live Demonstration Video Walkthrough • 60fps Web Cockpit</text>
  <rect x="1040" y="8" width="130" height="26" rx="6" fill="#ef4444" fill-opacity="0.2"/>
  <circle cx="1055" cy="21" r="4" fill="#ef4444"/>
  <text x="1068" y="25" fill="#fca5a5" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold">● LIVE DEMO</text>

  <!-- Video Playback Timeline Scrubber -->
  <rect x="40" y="52" width="1120" height="6" rx="3" fill="#1e293b"/>
  <rect class="anim-progress" x="40" y="52" width="0" height="6" rx="3" fill="#6366f1"/>

  <!-- Top Navigation & Stage Banner -->
  <g transform="translate(40, 75)">
    <rect x="0" y="0" width="1120" height="70" rx="12" fill="#0f172a" stroke="#334155"/>
    <rect x="20" y="15" width="40" height="40" rx="10" fill="url(#brandGrad)"/>
    <text x="75" y="38" fill="#ffffff" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold">Insurance Claims Intelligence Platform (ICIP)</text>
    <text x="75" y="54" fill="#94a3b8" font-size="11">Automated Evaluation: High-Risk Auto Collision Claim Ingestion</text>

    <!-- Narration Floating Pill -->
    <rect x="750" y="15" width="350" height="40" rx="20" fill="#4f46e5" fill-opacity="0.2" stroke="#6366f1"/>
    <text x="770" y="40" fill="#c7d2fe" font-size="12" font-weight="600">▶ Scene 2 of 5: Dual-Model ML Risk Scoring</text>
  </g>

  <!-- Live Form Demonstration Pane -->
  <g transform="translate(40, 165)">
    <!-- Left: Data Input Form -->
    <rect x="0" y="0" width="530" height="450" rx="14" fill="#0f172a" stroke="#334155"/>
    <text x="25" y="35" fill="#f8fafc" font-size="15" font-weight="bold">Live Data Ingestion &amp; Input Trigger</text>

    <text x="25" y="75" fill="#cbd5e1" font-size="11">Claimant &amp; Policy Identifier</text>
    <rect x="25" y="85" width="480" height="36" rx="6" fill="#1e293b" stroke="#475569"/>
    <text x="40" y="108" fill="#38bdf8" font-family="Courier New, monospace" font-size="12">CUST-89412 | POL-AUTO-2024-9914</text>

    <text x="25" y="145" fill="#cbd5e1" font-size="11">Claim Amount (Exceeding Coverage Limit)</text>
    <rect x="25" y="155" width="480" height="36" rx="6" fill="#1e293b" stroke="#ef4444" stroke-width="1.5"/>
    <text x="40" y="178" fill="#ef4444" font-family="Courier New, monospace" font-size="13" font-weight="bold">$45,000.00 USD</text>

    <text x="25" y="215" fill="#cbd5e1" font-size="11">Claim Incident Narrative (Simulated Real-time Input)</text>
    <rect x="25" y="225" width="480" height="100" rx="6" fill="#1e293b" stroke="#475569"/>
    <text class="anim-type" x="40" y="255" fill="#f8fafc" font-size="12">"Claimant reports sudden total collision at 02:15 AM on</text>
    <text class="anim-type" x="40" y="278" fill="#f8fafc" font-size="12">deserted highway, 3 days after policy start date.</text>
    <text class="anim-type" x="40" y="301" fill="#f8fafc" font-size="12">Mismatched VIN logged by emergency roadside dispatch."</text>

    <!-- Pulsing Action Button -->
    <rect class="anim-badge" x="25" y="355" width="480" height="50" rx="10" fill="#4f46e5" stroke="#6366f1"/>
    <text x="175" y="386" fill="#ffffff" font-size="15" font-weight="bold">⚡ Adjudicate Claim in 1.18ms</text>
  </g>

  <!-- Right: Real-Time Results & Evaluation Output -->
  <g transform="translate(610, 165)">
    <rect x="0" y="0" width="550" height="450" rx="14" fill="#0f172a" stroke="#334155"/>
    <text x="25" y="35" fill="#f8fafc" font-size="15" font-weight="bold">Autonomous Adjudication &amp; Fraud Verdict</text>

    <!-- Fraud Badge -->
    <rect class="anim-badge" x="25" y="65" width="500" height="60" rx="10" fill="#ef4444" fill-opacity="0.2" stroke="#ef4444" stroke-width="1.5"/>
    <text x="50" y="102" fill="#ef4444" font-family="Segoe UI, sans-serif" font-size="17" font-weight="bold">🚨 VERDICT: FRAUD_INVESTIGATION_FLAG</text>

    <!-- Gauge -->
    <text x="25" y="155" fill="#94a3b8" font-size="12" font-weight="bold">Composite Risk Radar (Isolation Forest + Rule Engine)</text>
    <rect x="25" y="170" width="500" height="22" rx="11" fill="#1e293b"/>
    <rect class="anim-gauge" x="25" y="170" width="0" height="22" rx="11" fill="url(#barGrad)"/>
    <text x="460" y="215" fill="#ef4444" font-size="15" font-weight="bold">89% RISK</text>

    <!-- Dual ML Cards -->
    <rect x="25" y="235" width="240" height="90" rx="8" fill="#1e293b" stroke="#334155"/>
    <text x="40" y="260" fill="#38bdf8" font-size="11" font-weight="bold">TF-IDF CLASSIFIER</text>
    <text x="40" y="285" fill="#ffffff" font-size="14" font-weight="bold">AUTO_COLLISION</text>
    <text x="40" y="305" fill="#34d399" font-size="10">98.4% Confidence • 1.18ms</text>

    <rect x="285" y="235" width="240" height="90" rx="8" fill="#1e293b" stroke="#ef4444"/>
    <text x="300" y="260" fill="#fca5a5" font-size="11" font-weight="bold">ISOLATION FOREST</text>
    <text x="300" y="285" fill="#ef4444" font-size="14" font-weight="bold">SCORE: -0.742</text>
    <text x="300" y="305" fill="#ef4444" font-size="10">Anomaly Flagged • 0.835 AUC</text>

    <!-- Rule Violations -->
    <rect x="25" y="340" width="500" height="85" rx="8" fill="#1e293b" stroke="#334155"/>
    <text x="40" y="365" fill="#fca5a5" font-size="11">❌ RULE-01: Claim $45,000 exceeds actual policy vehicle cash value.</text>
    <text x="40" y="385" fill="#fca5a5" font-size="11">❌ RULE-04: Loss event occurred 3 days after inception (&lt; 7 day threshold).</text>
    <text x="40" y="405" fill="#38bdf8" font-size="10">✓ Trace ID: `req-7f91-adjudicate-20261121` (Audited in MySQL)</text>
  </g>

  <!-- Bottom Player Bar Controls -->
  <g transform="translate(40, 635)">
    <rect x="0" y="0" width="1120" height="45" rx="10" fill="#090d16" stroke="#1e293b"/>
    <text x="25" y="28" fill="#ffffff" font-size="14">⏸ Pause</text>
    <text x="100" y="28" fill="#94a3b8" font-size="12">0:32 / 1:15</text>
    <text x="300" y="28" fill="#c7d2fe" font-size="12">Scene 1: BI Overview  |  <tspan fill="#ffffff" font-weight="bold">Scene 2: Live Claims Test</tspan>  |  Scene 3: Policy RAG  |  Scene 4: MLOps Drift</text>
    <text x="1020" y="28" fill="#38bdf8" font-size="12">1080p HD • Uma</text>
  </g>
</svg>"""
    (OUTPUT_DIR / "demo_video_walkthrough.svg").write_text(svg, encoding="utf-8")
    print("Generated demo_video_walkthrough.svg")


if __name__ == "__main__":
    generate_animated_walkthrough_svg()
