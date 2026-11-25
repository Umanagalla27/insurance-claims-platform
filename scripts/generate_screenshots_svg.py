"""Script to generate high-fidelity, vector-crisp SVG screenshots for ICIP documentation."""

from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "assets" / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_portal_overview_svg():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 680" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="brandGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4f46e5"/>
      <stop offset="100%" stop-color="#06b6d4"/>
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0.9"/>
    </linearGradient>
  </defs>

  <rect width="1200" height="680" fill="url(#bgGrad)"/>

  <!-- Top App Bar -->
  <rect x="0" y="0" width="1200" height="70" fill="#0f172a" opacity="0.9" stroke="#1e293b" stroke-width="1"/>
  <rect x="30" y="15" width="40" height="40" rx="10" fill="url(#brandGrad)"/>
  <text x="85" y="36" fill="#ffffff" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold">Insurance Claims Intelligence Platform</text>
  <text x="85" y="52" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="11">ICIP v1.0 • Gen AI &amp; Multi-Model Platform • Architected by Uma</text>

  <!-- Live Status Badge -->
  <rect x="850" y="20" width="170" height="30" rx="15" fill="#065f46" fill-opacity="0.2" stroke="#10b981" stroke-width="1"/>
  <circle cx="868" cy="35" r="4" fill="#34d399"/>
  <text x="880" y="40" fill="#34d399" font-family="Segoe UI, sans-serif" font-size="11" font-weight="600">All Systems Ready (173/173)</text>

  <rect x="1035" y="20" width="135" height="30" rx="8" fill="#4f46e5" fill-opacity="0.3" stroke="#6366f1" stroke-width="1"/>
  <text x="1050" y="39" fill="#c7d2fe" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold">▶ Live Video Tour</text>

  <!-- Nav Tabs -->
  <rect x="0" y="70" width="1200" height="45" fill="#090d16" stroke="#1e293b" stroke-width="1"/>
  <text x="50" y="98" fill="#818cf8" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" border-bottom="2">📊 Executive BI &amp; Analytics</text>
  <line x1="45" y1="113" x2="225" y2="113" stroke="#6366f1" stroke-width="3"/>
  <text x="260" y="98" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="13">⚡ Live Claims Adjudicator</text>
  <text x="470" y="98" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="13">🤖 Policy RAG AI Chatbot</text>
  <text x="670" y="98" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="13">🔬 MLOps Governance</text>
  <text x="860" y="98" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="13">🏛️ Cloud Topology</text>

  <!-- 4 Executive KPI Cards -->
  <g transform="translate(30, 135)">
    <!-- Card 1 -->
    <rect x="0" y="0" width="265" height="110" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="20" y="28" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="11" font-weight="600">AUDITED CLAIMS LIABILITY</text>
    <text x="20" y="65" fill="#ffffff" font-family="Segoe UI, sans-serif" font-size="28" font-weight="bold">$1.54B</text>
    <text x="20" y="92" fill="#38bdf8" font-family="Segoe UI, sans-serif" font-size="11">9,107 Verified Clean Records</text>

    <!-- Card 2 -->
    <rect x="290" y="0" width="265" height="110" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="310" y="28" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="11" font-weight="600">FRAUD LOSSES PREVENTED</text>
    <text x="310" y="65" fill="#f43f5e" font-family="Segoe UI, sans-serif" font-size="28" font-weight="bold">$69.6M</text>
    <text x="310" y="92" fill="#fb7185" font-family="Segoe UI, sans-serif" font-size="11">436 Isolation Forest Flags</text>

    <!-- Card 3 -->
    <rect x="580" y="0" width="265" height="110" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="600" y="28" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="11" font-weight="600">TOUCHLESS STP SETTLEMENT</text>
    <text x="600" y="65" fill="#10b981" font-family="Segoe UI, sans-serif" font-size="28" font-weight="bold">472 Claims</text>
    <text x="600" y="92" fill="#34d399" font-family="Segoe UI, sans-serif" font-size="11">5.18% Instant Settlement Rate</text>

    <!-- Card 4 -->
    <rect x="870" y="0" width="270" height="110" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="890" y="28" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="11" font-weight="600">PARQUET STORAGE SAVINGS</text>
    <text x="890" y="65" fill="#a855f7" font-family="Segoe UI, sans-serif" font-size="28" font-weight="bold">73.1%</text>
    <text x="890" y="92" fill="#c084fc" font-family="Segoe UI, sans-serif" font-size="11">1,066 KB down to 286.5 KB</text>
  </g>

  <!-- Main Chart Section -->
  <g transform="translate(30, 265)">
    <!-- Chart Box 1 -->
    <rect x="0" y="0" width="700" height="385" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="25" y="32" fill="#f8fafc" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold">Monthly Incurred Claims vs Payouts ($M)</text>
    <text x="25" y="52" fill="#64748b" font-family="Segoe UI, sans-serif" font-size="11">Kimball Star-Schema Verified Aggregation Pipeline</text>

    <!-- Grid lines -->
    <line x1="60" y1="90" x2="660" y2="90" stroke="#334155" stroke-dasharray="3,3"/>
    <text x="35" y="95" fill="#64748b" font-size="10">$150M</text>
    <line x1="60" y1="160" x2="660" y2="160" stroke="#334155" stroke-dasharray="3,3"/>
    <text x="35" y="165" fill="#64748b" font-size="10">$100M</text>
    <line x1="60" y1="230" x2="660" y2="230" stroke="#334155" stroke-dasharray="3,3"/>
    <text x="40" y="235" fill="#64748b" font-size="10">$50M</text>
    <line x1="60" y1="300" x2="660" y2="300" stroke="#334155"/>
    <text x="45" y="305" fill="#64748b" font-size="10">$0</text>

    <!-- Bars -->
    <!-- Jan -->
    <rect x="85" y="140" width="22" height="160" rx="4" fill="#6366f1"/>
    <rect x="110" y="190" width="22" height="110" rx="4" fill="#06b6d4"/>
    <text x="100" y="325" fill="#94a3b8" font-size="11">Jan</text>
    <!-- Feb -->
    <rect x="165" y="120" width="22" height="180" rx="4" fill="#6366f1"/>
    <rect x="190" y="170" width="22" height="130" rx="4" fill="#06b6d4"/>
    <text x="180" y="325" fill="#94a3b8" font-size="11">Feb</text>
    <!-- Mar -->
    <rect x="245" y="100" width="22" height="200" rx="4" fill="#6366f1"/>
    <rect x="270" y="150" width="22" height="150" rx="4" fill="#06b6d4"/>
    <text x="260" y="325" fill="#94a3b8" font-size="11">Mar</text>
    <!-- Apr -->
    <rect x="325" y="110" width="22" height="190" rx="4" fill="#6366f1"/>
    <rect x="350" y="165" width="22" height="135" rx="4" fill="#06b6d4"/>
    <text x="340" y="325" fill="#94a3b8" font-size="11">Apr</text>
    <!-- May -->
    <rect x="405" y="80" width="22" height="220" rx="4" fill="#6366f1"/>
    <rect x="430" y="130" width="22" height="170" rx="4" fill="#06b6d4"/>
    <text x="420" y="325" fill="#94a3b8" font-size="11">May</text>
    <!-- Jun -->
    <rect x="485" y="95" width="22" height="205" rx="4" fill="#6366f1"/>
    <rect x="510" y="145" width="22" height="155" rx="4" fill="#06b6d4"/>
    <text x="500" y="325" fill="#94a3b8" font-size="11">Jun</text>
    <!-- Jul -->
    <rect x="565" y="75" width="22" height="225" rx="4" fill="#6366f1"/>
    <rect x="590" y="125" width="22" height="175" rx="4" fill="#06b6d4"/>
    <text x="580" y="325" fill="#94a3b8" font-size="11">Jul</text>

    <!-- Legend -->
    <rect x="450" y="25" width="12" height="12" rx="3" fill="#6366f1"/>
    <text x="470" y="35" fill="#c7d2fe" font-size="11">Incurred Claims</text>
    <rect x="575" y="25" width="12" height="12" rx="3" fill="#06b6d4"/>
    <text x="595" y="35" fill="#a5f3fc" font-size="11">Settled Payouts</text>

    <!-- Loss Ratio Panel Box 2 -->
    <rect x="725" y="0" width="415" height="385" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="750" y="32" fill="#f8fafc" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold">Portfolio Loss Ratios &amp; STP Funnel</text>
    <text x="750" y="52" fill="#64748b" font-family="Segoe UI, sans-serif" font-size="11">Underwriting Profitability Target: &lt; 65%</text>

    <!-- Progress Bars -->
    <text x="750" y="90" fill="#e2e8f0" font-size="12" font-weight="600">Auto Collision (78.4%)</text>
    <rect x="750" y="100" width="365" height="14" rx="7" fill="#1e293b"/>
    <rect x="750" y="100" width="286" height="14" rx="7" fill="#f43f5e"/>

    <text x="750" y="145" fill="#e2e8f0" font-size="12" font-weight="600">Commercial Property (44.8%)</text>
    <rect x="750" y="155" width="365" height="14" rx="7" fill="#1e293b"/>
    <rect x="750" y="155" width="163" height="14" rx="7" fill="#10b981"/>

    <text x="750" y="200" fill="#e2e8f0" font-size="12" font-weight="600">Health Premier (62.1%)</text>
    <rect x="750" y="210" width="365" height="14" rx="7" fill="#1e293b"/>
    <rect x="750" y="210" width="226" height="14" rx="7" fill="#f59e0b"/>

    <text x="750" y="255" fill="#e2e8f0" font-size="12" font-weight="600">Home Secure (51.3%)</text>
    <rect x="750" y="265" width="365" height="14" rx="7" fill="#1e293b"/>
    <rect x="750" y="265" width="187" height="14" rx="7" fill="#3b82f6"/>

    <!-- Bottom summary box -->
    <rect x="750" y="300" width="365" height="65" rx="10" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="765" y="325" fill="#38bdf8" font-size="11" font-weight="bold">🎯 FinOps SLA Target Guaranteed</text>
    <text x="765" y="345" fill="#94a3b8" font-size="10">AWS $1.00 USD Budget Guardrail Active • Total Incurred Cloud Spend: $0.00</text>
  </g>
</svg>"""
    (OUTPUT_DIR / "portal_overview.svg").write_text(svg, encoding="utf-8")
    print("Generated portal_overview.svg")


def generate_claims_adjudicator_svg():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 680" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0.9"/>
    </linearGradient>
    <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="50%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#ef4444"/>
    </linearGradient>
  </defs>

  <rect width="1200" height="680" fill="url(#bgGrad)"/>

  <!-- Header -->
  <rect x="0" y="0" width="1200" height="70" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
  <text x="40" y="42" fill="#ffffff" font-family="Segoe UI, sans-serif" font-size="18" font-weight="bold">⚡ Live Claims Adjudicator &amp; Multi-Model Risk Engine</text>
  <text x="880" y="42" fill="#34d399" font-family="Segoe UI, sans-serif" font-size="12" font-weight="600">Model Inference p50: 1.18ms</text>

  <!-- Left Column: Input Form -->
  <g transform="translate(40, 95)">
    <rect x="0" y="0" width="540" height="555" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="25" y="35" fill="#f8fafc" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold">Claim Ingestion &amp; Parameters</text>
    <text x="25" y="55" fill="#94a3b8" font-size="11">Pre-fill realistic scenarios to test the dual-model ML pipeline</text>

    <!-- Sample Buttons -->
    <rect x="25" y="70" width="150" height="30" rx="8" fill="#10b981" fill-opacity="0.2" stroke="#10b981" stroke-width="1"/>
    <text x="38" y="90" fill="#34d399" font-size="11" font-weight="bold">✓ Low-Risk Medical (STP)</text>

    <rect x="185" y="70" width="160" height="30" rx="8" fill="#ef4444" fill-opacity="0.2" stroke="#ef4444" stroke-width="1"/>
    <text x="195" y="90" fill="#f87171" font-size="11" font-weight="bold">⚠️ High-Risk Collision (Fraud)</text>

    <rect x="355" y="70" width="155" height="30" rx="8" fill="#3b82f6" fill-opacity="0.2" stroke="#3b82f6" stroke-width="1"/>
    <text x="368" y="90" fill="#60a5fa" font-size="11" font-weight="bold">📋 Property Loss (Manual)</text>

    <!-- Inputs -->
    <text x="25" y="130" fill="#cbd5e1" font-size="12" font-weight="600">Claimant Identifier</text>
    <rect x="25" y="140" width="490" height="38" rx="8" fill="#0f172a" stroke="#475569"/>
    <text x="40" y="164" fill="#f8fafc" font-family="Courier New, monospace" font-size="13">CUST-89412 (Uma Nagalla)</text>

    <text x="25" y="205" fill="#cbd5e1" font-size="12" font-weight="600">Policy Identification Number</text>
    <rect x="25" y="215" width="490" height="38" rx="8" fill="#0f172a" stroke="#475569"/>
    <text x="40" y="239" fill="#f8fafc" font-family="Courier New, monospace" font-size="13">POL-AUTO-2024-9914</text>

    <text x="25" y="280" fill="#cbd5e1" font-size="12" font-weight="600">Claim Amount ($ USD)</text>
    <rect x="25" y="290" width="490" height="38" rx="8" fill="#0f172a" stroke="#ef4444" stroke-width="1.5"/>
    <text x="40" y="314" fill="#f87171" font-family="Courier New, monospace" font-size="14" font-weight="bold">$45,000.00 (Exceeds Policy Coverage)</text>

    <text x="25" y="355" fill="#cbd5e1" font-size="12" font-weight="600">Claim Narrative &amp; Description</text>
    <rect x="25" y="365" width="490" height="85" rx="8" fill="#0f172a" stroke="#475569"/>
    <text x="40" y="390" fill="#94a3b8" font-size="12">"Claimant reports sudden total vehicle rollover at 2:15 AM</text>
    <text x="40" y="410" fill="#94a3b8" font-size="12">on deserted highway, 3 days after policy inception date.</text>
    <text x="40" y="430" fill="#94a3b8" font-size="12">Mismatched VIN noted by emergency dispatch unit."</text>

    <!-- Run Engine Button -->
    <rect x="25" y="475" width="490" height="48" rx="10" fill="#4f46e5" stroke="#6366f1" stroke-width="1"/>
    <text x="180" y="505" fill="#ffffff" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold">⚡ Execute Adjudication Engine</text>
  </g>

  <!-- Right Column: Results & Radar -->
  <g transform="translate(610, 95)">
    <rect x="0" y="0" width="550" height="555" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="25" y="35" fill="#f8fafc" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold">Underwriting Adjudication Verdict</text>
    <text x="25" y="55" fill="#94a3b8" font-size="11">Dual-Model Evaluation (NLP Classifier + Isolation Forest)</text>

    <!-- Big Alert Banner -->
    <rect x="25" y="75" width="500" height="75" rx="10" fill="#ef4444" fill-opacity="0.15" stroke="#ef4444" stroke-width="1.5"/>
    <text x="45" y="110" fill="#ef4444" font-family="Segoe UI, sans-serif" font-size="18" font-weight="bold">🚨 FRAUD_INVESTIGATION_FLAG</text>
    <text x="45" y="132" fill="#fca5a5" font-size="11">Claim flagged for Special Investigations Unit (SIU) • 0% Straight-Through Tolerance</text>

    <!-- Risk Gauge -->
    <text x="25" y="180" fill="#cbd5e1" font-size="13" font-weight="bold">Composite Fraud Risk Score</text>
    <rect x="25" y="195" width="500" height="24" rx="12" fill="#0f172a"/>
    <rect x="25" y="195" width="445" height="24" rx="12" fill="url(#gaugeGrad)"/>
    <circle cx="470" cy="207" r="8" fill="#ffffff" stroke="#ef4444" stroke-width="2"/>
    <text x="485" y="240" fill="#ef4444" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold">89% Risk</text>

    <!-- Feature Breakdown Cards -->
    <g transform="translate(25, 260)">
      <rect x="0" y="0" width="240" height="110" rx="10" fill="#0f172a" stroke="#334155"/>
      <text x="15" y="25" fill="#94a3b8" font-size="11" font-weight="bold">NLP DOMAIN CLASSIFIER</text>
      <text x="15" y="55" fill="#38bdf8" font-size="18" font-weight="bold">AUTO_COLLISION</text>
      <text x="15" y="80" fill="#34d399" font-size="11">Confidence: 98.4% (p50: 1.18ms)</text>
      <text x="15" y="98" fill="#64748b" font-size="10">TF-IDF + Balanced LogReg</text>

      <rect x="260" y="0" width="240" height="110" rx="10" fill="#0f172a" stroke="#ef4444" stroke-width="1"/>
      <text x="275" y="25" fill="#fca5a5" font-size="11" font-weight="bold">ISOLATION FOREST ANOMALY</text>
      <text x="275" y="55" fill="#ef4444" font-size="18" font-weight="bold">SCORE: -0.742</text>
      <text x="275" y="80" fill="#ef4444" font-size="11">Anomaly Detected (AUC: 0.835)</text>
      <text x="275" y="98" fill="#64748b" font-size="10">10 Engineered Features</text>
    </g>

    <!-- Rule Violations Breakdown -->
    <g transform="translate(25, 390)">
      <rect x="0" y="0" width="500" height="135" rx="10" fill="#0f172a" stroke="#334155"/>
      <text x="15" y="25" fill="#f8fafc" font-size="12" font-weight="bold">Underwriting Business Rule Violations Triggered:</text>
      <text x="15" y="50" fill="#fb7185" font-size="11">❌ RULE-01: Claim amount ($45,000) exceeds vehicle actual cash value.</text>
      <text x="15" y="72" fill="#fb7185" font-size="11">❌ RULE-04: Loss event occurred within 7 days of policy bind date.</text>
      <text x="15" y="94" fill="#fb7185" font-size="11">❌ RULE-08: Crash time (02:15 AM) matches high-loss fraud cohort.</text>
      <text x="15" y="118" fill="#38bdf8" font-size="11">ℹ️ Trace Correlation ID: `req-7f91-adjudicate-20261121`</text>
    </g>
  </g>
</svg>"""
    (OUTPUT_DIR / "claims_adjudicator.svg").write_text(svg, encoding="utf-8")
    print("Generated claims_adjudicator.svg")


def generate_policy_rag_svg():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 680" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0.9"/>
    </linearGradient>
  </defs>

  <rect width="1200" height="680" fill="url(#bgGrad)"/>

  <!-- Header -->
  <rect x="0" y="0" width="1200" height="70" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
  <text x="40" y="42" fill="#ffffff" font-family="Segoe UI, sans-serif" font-size="18" font-weight="bold">🤖 Policy RAG AI Chatbot (Hybrid FAISS + BM25 Search)</text>
  <text x="860" y="42" fill="#38bdf8" font-family="Segoe UI, sans-serif" font-size="12" font-weight="600">Reciprocal Rank Fusion (k=60) • 66 Clauses</text>

  <!-- Prompt Chips -->
  <g transform="translate(40, 85)">
    <rect x="0" y="0" width="350" height="32" rx="8" fill="#1e293b" stroke="#38bdf8" stroke-width="1"/>
    <text x="15" y="21" fill="#38bdf8" font-size="11">❓ Are flood and water damage covered under Home Secure?</text>

    <rect x="370" y="0" width="340" height="32" rx="8" fill="#1e293b" stroke="#475569"/>
    <text x="385" y="21" fill="#94a3b8" font-size="11">❓ What is the waiting period for pre-existing medical conditions?</text>

    <rect x="730" y="0" width="280" height="32" rx="8" fill="#1e293b" stroke="#475569"/>
    <text x="745" y="21" fill="#94a3b8" font-size="11">❓ What is the grace period for premium renewals?</text>
  </g>

  <!-- Chat Dialog Area -->
  <g transform="translate(40, 135)">
    <rect x="0" y="0" width="1120" height="435" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>

    <!-- User Message -->
    <g transform="translate(400, 30)">
      <rect x="0" y="0" width="680" height="55" rx="12" fill="#4f46e5" fill-opacity="0.25" stroke="#6366f1" stroke-width="1"/>
      <text x="20" y="25" fill="#c7d2fe" font-size="11" font-weight="bold">UMA (Claims Adjuster)</text>
      <text x="20" y="45" fill="#ffffff" font-size="13">"Are water damage and flooding covered under Home Secure Policy contracts?"</text>
    </g>

    <!-- AI Bot Message -->
    <g transform="translate(40, 105)">
      <rect x="0" y="0" width="850" height="230" rx="12" fill="#0f172a" stroke="#334155" stroke-width="1"/>
      <text x="25" y="30" fill="#38bdf8" font-size="11" font-weight="bold">ICIP POLICY RAG ASSISTANT</text>
      <text x="220" y="30" fill="#34d399" font-size="10">✓ Grounded via Dense Cosine + Sparse BM25 Fusion (18.4ms)</text>

      <text x="25" y="60" fill="#e2e8f0" font-size="13">Under the standard <tspan font-weight="bold" fill="#ffffff">Home Secure Policy (Policy Type: HOME_SECURE)</tspan>, water damage caused by</text>
      <text x="25" y="82" fill="#e2e8f0" font-size="13">natural flooding, surface runoff, or sewer backup is <tspan font-weight="bold" fill="#ef4444">STRICTLY EXCLUDED</tspan> from base coverage.</text>
      <text x="25" y="104" fill="#e2e8f0" font-size="13">Sudden and accidental internal plumbing discharge is covered up to policy limits.</text>

      <!-- Grounded Citation Box -->
      <rect x="25" y="130" width="800" height="75" rx="8" fill="#1e293b" stroke="#38bdf8" stroke-dasharray="2,2"/>
      <text x="40" y="152" fill="#38bdf8" font-size="11" font-weight="bold">📌 Verified Clause Citation: [Clause SEC-4.2 - Water Damage Exclusions]</text>
      <text x="40" y="172" fill="#94a3b8" font-size="11">"Section 4.2: Loss or damage caused directly or indirectly by tidal surge, surface water, overflow of bodies</text>
      <text x="40" y="190" fill="#94a3b8" font-size="11">of water, or water that backs up through sewers or drains is uninsurable under standard terms."</text>
    </g>

    <!-- Retrieval Metrics Strip -->
    <g transform="translate(40, 360)">
      <rect x="0" y="0" width="1040" height="50" rx="8" fill="#0f172a" stroke="#334155"/>
      <text x="20" y="30" fill="#94a3b8" font-size="11">Dense Vector (FAISS): <tspan fill="#34d399" font-weight="bold">Cosine Similarity 0.941</tspan></text>
      <text x="320" y="30" fill="#94a3b8" font-size="11">Lexical (BM25): <tspan fill="#38bdf8" font-weight="bold">Score 18.72</tspan></text>
      <text x="560" y="30" fill="#94a3b8" font-size="11">RRF Rank Score: <tspan fill="#a855f7" font-weight="bold">0.0328</tspan></text>
      <text x="800" y="30" fill="#94a3b8" font-size="11">Cache Status: <tspan fill="#10b981" font-weight="bold">LRU HIT (0.42ms)</tspan></text>
    </g>
  </g>

  <!-- Input Field Bar -->
  <g transform="translate(40, 590)">
    <rect x="0" y="0" width="980" height="48" rx="10" fill="#1e293b" stroke="#475569"/>
    <text x="25" y="30" fill="#94a3b8" font-size="13">Ask any question regarding coverage limits, waiting periods, or policy exclusions...</text>
    <rect x="1000" y="0" width="160" height="48" rx="10" fill="#4f46e5" stroke="#6366f1"/>
    <text x="1040" y="30" fill="#ffffff" font-size="14" font-weight="bold">Send Query</text>
  </g>
</svg>"""
    (OUTPUT_DIR / "policy_rag_chatbot.svg").write_text(svg, encoding="utf-8")
    print("Generated policy_rag_chatbot.svg")


def generate_mlops_drift_svg():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 680" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0.9"/>
    </linearGradient>
  </defs>

  <rect width="1200" height="680" fill="url(#bgGrad)"/>

  <!-- Header -->
  <rect x="0" y="0" width="1200" height="70" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
  <text x="40" y="42" fill="#ffffff" font-family="Segoe UI, sans-serif" font-size="18" font-weight="bold">🔬 MLOps Model Governance &amp; Covariate Drift Engine</text>
  <text x="830" y="42" fill="#c084fc" font-family="Segoe UI, sans-serif" font-size="12" font-weight="600">Automated Retraining Threshold: PSI &gt; 0.25</text>

  <!-- Drift Trigger Banner -->
  <g transform="translate(40, 90)">
    <rect x="0" y="0" width="1120" height="60" rx="10" fill="#ef4444" fill-opacity="0.15" stroke="#ef4444" stroke-width="1.5"/>
    <text x="25" y="35" fill="#ef4444" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold">🚨 CRITICAL DATA DRIFT DETECTED: Kolmogorov-Smirnov p-value = 0.0000 | PSI = 0.3120</text>
    <text x="750" y="35" fill="#fca5a5" font-size="12" font-weight="bold">Action: Candidate Model Staged for Retraining</text>
  </g>

  <!-- Drift Table -->
  <g transform="translate(40, 170)">
    <rect x="0" y="0" width="1120" height="280" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="25" y="35" fill="#f8fafc" font-size="15" font-weight="bold">Feature Drift Monitoring Matrix (KS Test &amp; Population Stability Index)</text>

    <!-- Table Header -->
    <rect x="25" y="55" width="1070" height="35" fill="#0f172a" rx="6"/>
    <text x="45" y="78" fill="#94a3b8" font-size="11" font-weight="bold">FEATURE NAME</text>
    <text x="220" y="78" fill="#94a3b8" font-size="11" font-weight="bold">DATA TYPE</text>
    <text x="360" y="78" fill="#94a3b8" font-size="11" font-weight="bold">PSI METRIC</text>
    <text x="500" y="78" fill="#94a3b8" font-size="11" font-weight="bold">P-VALUE</text>
    <text x="640" y="78" fill="#94a3b8" font-size="11" font-weight="bold">STATISTICAL TEST</text>
    <text x="820" y="78" fill="#94a3b8" font-size="11" font-weight="bold">SEVERITY</text>
    <text x="960" y="78" fill="#94a3b8" font-size="11" font-weight="bold">STATUS</text>

    <!-- Row 1 -->
    <text x="45" y="118" fill="#ffffff" font-family="Courier New, monospace" font-size="12">claim_amount</text>
    <text x="220" y="118" fill="#94a3b8" font-size="11">continuous</text>
    <text x="360" y="118" fill="#ef4444" font-size="12" font-weight="bold">0.3120</text>
    <text x="500" y="118" fill="#ef4444" font-family="Courier New, monospace" font-size="12">0.000e+00</text>
    <text x="640" y="118" fill="#cbd5e1" font-size="11">Two-Sample KS Test</text>
    <rect x="815" y="103" width="70" height="20" rx="4" fill="#ef4444" fill-opacity="0.2"/>
    <text x="825" y="117" fill="#f87171" font-size="10" font-weight="bold">CRITICAL</text>
    <text x="960" y="118" fill="#ef4444" font-size="11" font-weight="bold">Drift Detected</text>
    <line x1="25" y1="135" x2="1095" y2="135" stroke="#334155"/>

    <!-- Row 2 -->
    <text x="45" y="160" fill="#ffffff" font-family="Courier New, monospace" font-size="12">claim_frequency</text>
    <text x="220" y="160" fill="#94a3b8" font-size="11">continuous</text>
    <text x="360" y="160" fill="#f59e0b" font-size="12" font-weight="bold">0.1420</text>
    <text x="500" y="160" fill="#cbd5e1" font-family="Courier New, monospace" font-size="12">0.0381</text>
    <text x="640" y="160" fill="#cbd5e1" font-size="11">Two-Sample KS Test</text>
    <rect x="815" y="145" width="70" height="20" rx="4" fill="#f59e0b" fill-opacity="0.2"/>
    <text x="825" y="159" fill="#fbbf24" font-size="10" font-weight="bold">WARNING</text>
    <text x="960" y="160" fill="#fbbf24" font-size="11">Moderate Shift</text>
    <line x1="25" y1="177" x2="1095" y2="177" stroke="#334155"/>

    <!-- Row 3 -->
    <text x="45" y="202" fill="#ffffff" font-family="Courier New, monospace" font-size="12">policy_type</text>
    <text x="220" y="202" fill="#94a3b8" font-size="11">categorical</text>
    <text x="360" y="202" fill="#10b981" font-size="12" font-weight="bold">0.0041</text>
    <text x="500" y="202" fill="#cbd5e1" font-family="Courier New, monospace" font-size="12">0.9650</text>
    <text x="640" y="202" fill="#cbd5e1" font-size="11">Chi-Square Goodness</text>
    <rect x="815" y="187" width="70" height="20" rx="4" fill="#10b981" fill-opacity="0.2"/>
    <text x="830" y="201" fill="#34d399" font-size="10" font-weight="bold">NONE</text>
    <text x="960" y="202" fill="#34d399" font-size="11">Stable Baseline</text>
    <line x1="25" y1="219" x2="1095" y2="219" stroke="#334155"/>

    <!-- Row 4 -->
    <text x="45" y="244" fill="#ffffff" font-family="Courier New, monospace" font-size="12">claim_priority</text>
    <text x="220" y="244" fill="#94a3b8" font-size="11">categorical</text>
    <text x="360" y="244" fill="#10b981" font-size="12" font-weight="bold">0.0019</text>
    <text x="500" y="244" fill="#cbd5e1" font-family="Courier New, monospace" font-size="12">0.9910</text>
    <text x="640" y="244" fill="#cbd5e1" font-size="11">Chi-Square Goodness</text>
    <rect x="815" y="229" width="70" height="20" rx="4" fill="#10b981" fill-opacity="0.2"/>
    <text x="830" y="243" fill="#34d399" font-size="10" font-weight="bold">NONE</text>
    <text x="960" y="244" fill="#34d399" font-size="11">Stable Baseline</text>
  </g>

  <!-- Model Registry Cards -->
  <g transform="translate(40, 470)">
    <!-- Production Model -->
    <rect x="0" y="0" width="540" height="150" rx="12" fill="url(#cardGrad)" stroke="#334155"/>
    <text x="20" y="30" fill="#f8fafc" font-size="13" font-weight="bold">ACTIVE PRODUCTION MODEL: Isolation Forest Anomaly v1.0.0</text>
    <rect x="420" y="15" width="100" height="22" rx="4" fill="#10b981" fill-opacity="0.2"/>
    <text x="435" y="30" fill="#34d399" font-size="10" font-weight="bold">PRODUCTION</text>
    <text x="20" y="60" fill="#94a3b8" font-size="11">Trained: 2026-11-20 • ROC-AUC: <tspan fill="#34d399" font-weight="bold">0.8349</tspan> • Features: 10 Dimensions</text>
    <text x="20" y="85" fill="#94a3b8" font-size="11">Deployment: AWS EC2 / Docker Compose Gateway • Memory: 142 MB</text>
    <text x="20" y="115" fill="#f59e0b" font-size="11">⚠️ Drift Warning: 1 continuous feature tripped critical threshold ($PSI &gt; 0.25)</text>

    <!-- Staged Candidate -->
    <rect x="580" y="0" width="540" height="150" rx="12" fill="url(#cardGrad)" stroke="#10b981" stroke-width="1.5"/>
    <text x="600" y="30" fill="#f8fafc" font-size="13" font-weight="bold">STAGED CANDIDATE: Isolation Forest Anomaly v1.1.0-rc1</text>
    <rect x="1000" y="15" width="100" height="22" rx="4" fill="#38bdf8" fill-opacity="0.2"/>
    <text x="1025" y="30" fill="#38bdf8" font-size="10" font-weight="bold">STAGING</text>
    <text x="600" y="60" fill="#94a3b8" font-size="11">Auto-triggered via: <tspan fill="#ffffff" font-family="Courier New">ml/retraining_trigger.py</tspan></text>
    <text x="600" y="85" fill="#94a3b8" font-size="11">New Training Dataset: 10,300 recent audited warehouse claims</text>
    <text x="600" y="115" fill="#34d399" font-size="11" font-weight="bold">✓ Candidate Validated: ROC-AUC 0.8612 • Ready for Zero-Downtime Rollout</text>
  </g>
</svg>"""
    (OUTPUT_DIR / "mlops_drift_monitor.svg").write_text(svg, encoding="utf-8")
    print("Generated mlops_drift_monitor.svg")


def generate_architecture_topology_svg():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 680" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#020617"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="boxGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
  </defs>

  <rect width="1200" height="680" fill="url(#bgGrad)"/>

  <!-- Title -->
  <text x="40" y="45" fill="#ffffff" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold">🏛️ End-to-End Enterprise Architecture Topology</text>
  <text x="40" y="70" fill="#94a3b8" font-family="Segoe UI, sans-serif" font-size="12">Insurance Claims Intelligence Platform (ICIP) • Multi-Cloud &amp; Hybrid Microservices</text>

  <!-- Layer 1: Ingestion -->
  <g transform="translate(40, 100)">
    <rect x="0" y="0" width="250" height="520" rx="14" fill="url(#boxGrad)" stroke="#334155" stroke-width="1"/>
    <text x="20" y="35" fill="#38bdf8" font-size="14" font-weight="bold">1. INGESTION &amp; ETL</text>

    <rect x="20" y="60" width="210" height="90" rx="8" fill="#0f172a" stroke="#475569"/>
    <text x="35" y="85" fill="#ffffff" font-size="12" font-weight="bold">Mock Claims REST API</text>
    <text x="35" y="105" fill="#94a3b8" font-size="10">FastAPI :8001 • Token Bucket</text>
    <text x="35" y="125" fill="#34d399" font-size="10">50 req/sec • 10,300 Claims</text>

    <rect x="20" y="170" width="210" height="90" rx="8" fill="#0f172a" stroke="#475569"/>
    <text x="35" y="195" fill="#ffffff" font-size="12" font-weight="bold">Resilient Extractor</text>
    <text x="35" y="215" fill="#94a3b8" font-size="10">Tenacity Backoff &amp; Jitter</text>
    <text x="35" y="235" fill="#f59e0b" font-size="10">Auto-Retry on HTTP 429</text>

    <rect x="20" y="280" width="210" height="90" rx="8" fill="#0f172a" stroke="#ef4444"/>
    <text x="35" y="305" fill="#fca5a5" font-size="12" font-weight="bold">Dead-Letter Quarantine</text>
    <text x="35" y="325" fill="#94a3b8" font-size="10">JSON Lines Audit Log</text>
    <text x="35" y="345" fill="#ef4444" font-size="10">1,193 Invalid Claims Held</text>

    <rect x="20" y="390" width="210" height="90" rx="8" fill="#0f172a" stroke="#475569"/>
    <text x="35" y="415" fill="#ffffff" font-size="12" font-weight="bold">Serverless Lambda</text>
    <text x="35" y="435" fill="#94a3b8" font-size="10">AWS S3 Event Trigger</text>
    <text x="35" y="455" fill="#38bdf8" font-size="10">128MB Memory Execution</text>
  </g>

  <!-- Layer 2: Warehouse -->
  <g transform="translate(325, 100)">
    <rect x="0" y="0" width="250" height="520" rx="14" fill="url(#boxGrad)" stroke="#334155" stroke-width="1"/>
    <text x="20" y="35" fill="#10b981" font-size="14" font-weight="bold">2. WAREHOUSE &amp; BI</text>

    <rect x="20" y="60" width="210" height="110" rx="8" fill="#0f172a" stroke="#10b981"/>
    <text x="35" y="85" fill="#ffffff" font-size="12" font-weight="bold">MySQL 8.4 Warehouse</text>
    <text x="35" y="105" fill="#94a3b8" font-size="10">Covering B-Tree Indexes</text>
    <text x="35" y="125" fill="#34d399" font-size="10">8.94x Speedup (1.3ms seek)</text>
    <text x="35" y="145" fill="#94a3b8" font-size="10">9,107 Clean Rows ($1.54B)</text>

    <rect x="20" y="190" width="210" height="100" rx="8" fill="#0f172a" stroke="#475569"/>
    <text x="35" y="215" fill="#ffffff" font-size="12" font-weight="bold">Kimball Star-Schema</text>
    <text x="35" y="235" fill="#94a3b8" font-size="10">Fact &amp; Conformed Dims</text>
    <text x="35" y="255" fill="#38bdf8" font-size="10">Power BI Tabular Model</text>
    <text x="35" y="275" fill="#94a3b8" font-size="10">Certified DAX Measures</text>

    <rect x="20" y="310" width="210" height="100" rx="8" fill="#0f172a" stroke="#a855f7"/>
    <text x="35" y="335" fill="#ffffff" font-size="12" font-weight="bold">Snappy Apache Parquet</text>
    <text x="35" y="355" fill="#94a3b8" font-size="10">Cold Storage Snapshots</text>
    <text x="35" y="375" fill="#c084fc" font-size="10">73.1% Disk Reduction</text>
    <text x="35" y="395" fill="#34d399" font-size="10">SHA-256 Checksum Validated</text>
  </g>

  <!-- Layer 3: ML & AI -->
  <g transform="translate(610, 100)">
    <rect x="0" y="0" width="250" height="520" rx="14" fill="url(#boxGrad)" stroke="#334155" stroke-width="1"/>
    <text x="20" y="35" fill="#f43f5e" font-size="14" font-weight="bold">3. ML &amp; HYBRID RAG</text>

    <rect x="20" y="60" width="210" height="95" rx="8" fill="#0f172a" stroke="#475569"/>
    <text x="35" y="85" fill="#ffffff" font-size="12" font-weight="bold">TF-IDF NLP Classifier</text>
    <text x="35" y="105" fill="#94a3b8" font-size="10">Domain Categorization</text>
    <text x="35" y="125" fill="#34d399" font-size="10">1.18ms p50 Inference</text>
    <text x="35" y="142" fill="#94a3b8" font-size="10">Macro F1: 0.94</text>

    <rect x="20" y="175" width="210" height="95" rx="8" fill="#0f172a" stroke="#ef4444"/>
    <text x="35" y="200" fill="#ffffff" font-size="12" font-weight="bold">Isolation Forest Anomaly</text>
    <text x="35" y="220" fill="#94a3b8" font-size="10">10 Engineered Features</text>
    <text x="35" y="240" fill="#fca5a5" font-size="10">0.835 ROC-AUC</text>
    <text x="35" y="258" fill="#ef4444" font-size="10">$69.6M Fraud Detected</text>

    <rect x="20" y="290" width="210" height="100" rx="8" fill="#0f172a" stroke="#38bdf8"/>
    <text x="35" y="315" fill="#ffffff" font-size="12" font-weight="bold">Dense FAISS Vector DB</text>
    <text x="35" y="335" fill="#94a3b8" font-size="10">66 Semantic Chunks</text>
    <text x="35" y="355" fill="#38bdf8" font-size="10">Cosine Similarity Index</text>
    <text x="35" y="375" fill="#94a3b8" font-size="10">Sub-millisecond Search</text>

    <rect x="20" y="410" width="210" height="90" rx="8" fill="#0f172a" stroke="#475569"/>
    <text x="35" y="435" fill="#ffffff" font-size="12" font-weight="bold">Hybrid BM25 + RRF</text>
    <text x="35" y="455" fill="#94a3b8" font-size="10">Lexical + Dense Fusion</text>
    <text x="35" y="475" fill="#34d399" font-size="10">k=60 Reciprocal Ranking</text>
  </g>

  <!-- Layer 4: Gateway & SRE -->
  <g transform="translate(895, 100)">
    <rect x="0" y="0" width="265" height="520" rx="14" fill="url(#boxGrad)" stroke="#334155" stroke-width="1"/>
    <text x="20" y="35" fill="#c084fc" font-size="14" font-weight="bold">4. GATEWAY &amp; SRE</text>

    <rect x="20" y="60" width="225" height="95" rx="8" fill="#0f172a" stroke="#6366f1"/>
    <text x="35" y="85" fill="#ffffff" font-size="12" font-weight="bold">FastAPI Core Gateway</text>
    <text x="35" y="105" fill="#94a3b8" font-size="10">ASGI Timing Middleware</text>
    <text x="35" y="125" fill="#c7d2fe" font-size="10">ServiceContainer Lifespan</text>
    <text x="35" y="142" fill="#34d399" font-size="10">Serving Web Portal at /</text>

    <rect x="20" y="175" width="225" height="95" rx="8" fill="#0f172a" stroke="#10b981"/>
    <text x="35" y="200" fill="#ffffff" font-size="12" font-weight="bold">Kubernetes SRE Probes</text>
    <text x="35" y="220" fill="#94a3b8" font-size="10">/health/live (Liveness)</text>
    <text x="35" y="240" fill="#94a3b8" font-size="10">/health/ready (Readiness)</text>
    <text x="35" y="258" fill="#34d399" font-size="10">Prometheus /metrics</text>

    <rect x="20" y="290" width="225" height="95" rx="8" fill="#0f172a" stroke="#475569"/>
    <text x="35" y="315" fill="#ffffff" font-size="12" font-weight="bold">MLOps Drift Engine</text>
    <text x="35" y="335" fill="#94a3b8" font-size="10">KS-Test &amp; PSI Statistics</text>
    <text x="35" y="355" fill="#f59e0b" font-size="10">JSON Model Registry</text>
    <text x="35" y="372" fill="#34d399" font-size="10">Automated Retraining</text>

    <rect x="20" y="405" width="225" height="95" rx="8" fill="#0f172a" stroke="#10b981"/>
    <text x="35" y="430" fill="#ffffff" font-size="12" font-weight="bold">AWS Cloud FinOps</text>
    <text x="35" y="450" fill="#94a3b8" font-size="10">$1.00 USD Budget Alarm</text>
    <text x="35" y="470" fill="#34d399" font-size="10">Incurred Cost: $0.00</text>
    <text x="35" y="488" fill="#94a3b8" font-size="10">Automated Teardown Script</text>
  </g>
</svg>"""
    (OUTPUT_DIR / "architecture_topology.svg").write_text(svg, encoding="utf-8")
    print("Generated architecture_topology.svg")


if __name__ == "__main__":
    generate_portal_overview_svg()
    generate_claims_adjudicator_svg()
    generate_policy_rag_svg()
    generate_mlops_drift_svg()
    generate_architecture_topology_svg()
    print("All 5 vector SVG screenshots generated successfully in docs/assets/screenshots/!")
