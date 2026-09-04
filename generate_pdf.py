import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak, KeepTogether

OUTPUT_PDF = Path(r"C:\Users\III S I\.gemini\antigravity\scratch\reviv-ai-l\Reviv_AI_l_Submission_and_Pitch_Dossier.pdf")

def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    primary_color = colors.HexColor("#0f172a") # Slate 900
    brand_blue = colors.HexColor("#0284c7")    # Sky 600
    accent_emerald = colors.HexColor("#059669")# Emerald 600
    accent_amber = colors.HexColor("#d97706")  # Amber 600
    dark_gray = colors.HexColor("#334155")
    bg_light = colors.HexColor("#f8fafc")
    bg_blue_light = colors.HexColor("#f0f9ff")
    border_color = colors.HexColor("#cbd5e1")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=2
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=brand_blue,
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12.5,
        leading=16,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=4
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=brand_blue,
        spaceBefore=6,
        spaceAfter=2
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=dark_gray,
        spaceAfter=4
    )

    cue_style = ParagraphStyle(
        'VisualCue',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#b91c1c")
    )

    speech_style = ParagraphStyle(
        'SpokenSpeech',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Reviv-AI-l: Official Submission & Stage-Directed Pitch Dossier", title_style))
    story.append(Paragraph("Razorpay AI Buildathon 2026 — Track 3: AI Revenue Recovery", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_blue, spaceBefore=0, spaceAfter=8))

    meta_data = [
        [Paragraph("<b>Candidate Name:</b>", body_style), Paragraph("Mohammad Zishan Alam", body_style),
         Paragraph("<b>Email:</b>", body_style), Paragraph("alamzishan07@gmail.com", body_style)],
        [Paragraph("<b>Selected Track:</b>", body_style), Paragraph("Track 03 — AI Revenue Recovery", body_style),
         Paragraph("<b>GitHub Repo:</b>", body_style), Paragraph("github.com/MohammadZishanAlam/reviv-ai-l", body_style)],
        [Paragraph("<b>Tech Stack:</b>", body_style), Paragraph("FastAPI, SQLite, SQLAlchemy, WebSockets", body_style),
         Paragraph("<b>AI Engine:</b>", body_style), Paragraph("Gemini 2.0 Flash + Heuristic Failover Core", body_style)]
    ]
    t_meta = Table(meta_data, colWidths=[85, 175, 75, 205])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 8))

    # SECTION 1: GOOGLE FORM ANSWERS
    story.append(Paragraph("SECTION 1: THE FOUR CORE EVALUATION ANSWERS (FOR GOOGLE FORM)", h1_style))
    
    story.append(Paragraph("1. Problem Taste — Did you pick something that actually matters?", h2_style))
    p1 = ("In Indian digital commerce, 15% to 25% of checkouts fail prematurely due to transient bank Core Banking System (CBS) downtime, UPI ceiling limits, or OTP session friction. Today, merchants lose this revenue in one of two broken ways: (1) They do nothing, forfeiting up to 20% of GMV. (2) They use 'dumb dunning'—spamming customers with immediate SMS retry links while the issuer bank is experiencing an active outage. The customer clicks, it fails again, and they abandon the merchant permanently. We built <b>Reviv-AI-l</b> because payment failure recovery directly expands GMV for merchants and transaction fee revenue for Razorpay. Rather than creating a generic shopping chatbot, we engineered an autonomous recovery layer addressing the single biggest drop-off point in the payments funnel.")
    story.append(Paragraph(p1, body_style))

    story.append(Paragraph("2. Build Quality — Does it run, is it structured, would you trust it?", h2_style))
    p2 = ("Reviv-AI-l is a production-grade, full-stack application backed by an automated test suite (9/9 tests passing):<br/>"
          "• <b>Architecture & Persistence:</b> Powered by a FastAPI backend with SQLite/SQLAlchemy persistence, modeling transactions, recovery attempts, bank health telemetry, and audit trails.<br/>"
          "• <b>Cryptographic Security:</b> Ingests live Razorpay webhooks with mandatory HMAC-SHA256 signature verification matching Razorpay's exact spec (x-razorpay-signature). Tampered payloads are rejected with HTTP 400.<br/>"
          "• <b>Idempotency Gate:</b> Webhook deliveries are deduplicated by transaction ID, preventing duplicate dunning dispatches or double charges.<br/>"
          "• <b>Batch Benchmark Engine:</b> Features a 25-transaction batch benchmark engine (via POST /api/simulate/batch & CLI batch_recovery_test.py) validating the Track 3 bar: measured recovery, compliant escalation, stopping rules, and audit logs.<br/>"
          "• <b>Real Tool Execution:</b> Interfaces directly with Razorpay's REST APIs (/v1/payment_links) to generate dynamic, bounded recovery payment links with custom expiry TTLs.<br/>"
          "• <b>Real-Time Command Center:</b> A reactive dashboard connected via WebSockets (/ws) providing live GMV metrics, an interactive 1-click failure simulator, batch benchmark modal, and realistic WhatsApp customer outreach previews.")
    story.append(Paragraph(p2, body_style))

    story.append(Paragraph("3. AI Judgment — The right tool in the right place, and where you chose not to use one.", h2_style))
    p3 = ("Our design principle was strict: <b>LLMs for semantic error diagnosis; deterministic code for financial math and execution.</b><br/>"
          "<b>Where we used AI:</b> (1) Unstructured Error Taxonomy: We use Google Gemini Flash to parse raw bank codes (error_source, error_step, error_reason) and telemetry into 5 operational classes (BANK_DOWNTIME_TRANSIENT, USER_LIMIT_EXCEEDED, AUTH_FRICTION_TIMEOUT, PAYMENT_METHOD_INELIGIBLE, HARD_FAILURE_IRRECOVERABLE). (2) Empathetic Outreach: The agent synthesizes polite, context-aware recovery notifications tailored to the root cause.<br/>"
          "<b>Where we explicitly avoided AI:</b> (1) Financial Math: Subtotals, paise-to-rupee conversions, and dynamic 5% cart recovery discounts are 100% deterministic code. (2) Hard Stopping Rules: If a card is reported stolen, blocked, or fraudulent (HARD_FAILURE_IRRECOVERABLE), an LLM cannot negotiate or override. Dunning halts immediately with zero outreach, and an immutable audit log is generated.")
    story.append(Paragraph(p3, body_style))

    story.append(Paragraph("4. Failure Recovery — What broke, and what you did about it.", h2_style))
    p4 = ("We addressed failure recovery on two fronts:<br/>"
          "1. <b>The Domain Level (Payment Failure Resiliency):</b> When an issuer CBS experiences an outage (e.g., SBI UPI 504 timeouts), immediate retries cause retry storms. Reviv-AI-l implements an issuer health circuit breaker: if bank health is degraded, outreach is automatically queued with a 15–30 minute delay, re-engaging the buyer only when bank rails stabilize.<br/>"
          "2. <b>The Engineering Level (System Resilience):</b> (a) <i>LLM Failover:</i> External AI APIs can encounter rate limits or timeouts. We engineered a dual-engine architecture: if Gemini fails or times out, the system fails over to a deterministic heuristic rule matrix in &lt;5ms. Recovery is never blocked. (b) <i>Webhook Race Conditions:</i> Razorpay retries unacknowledged webhooks. We fixed duplicate links with an atomic database check and event lock before orchestrating actions. (c) <i>Windows Console Compatibility:</i> CLI test runners threw UnicodeEncodeError on Windows CP1252 consoles. We added sys.stdout.reconfigure(encoding='utf-8') for clean cross-platform execution.")
    story.append(Paragraph(p4, body_style))

    story.append(PageBreak())

    # SECTION 2: STAGE-DIRECTED SPEECH SCRIPT
    story.append(Paragraph("SECTION 2: COMPLETE STAGE-DIRECTED VIDEO PITCH & DEMO SCRIPT", h1_style))
    story.append(Paragraph("<b>Screen Setup Instructions:</b> Put your PowerShell terminal on the <b>Left Half</b> of your screen and your Browser at <code>http://localhost:8000</code> on the <b>Right Half</b>. This split view proves live backend execution.", body_style))
    story.append(HRFlowable(width="100%", thickness=1, color=border_color, spaceBefore=4, spaceAfter=8))

    # Directional Script Table
    script_data = [
        [
            Paragraph("<b>Timestamp & What to Open/Click</b>", ParagraphStyle('Hdr1', parent=body_style, fontName='Helvetica-Bold', textColor=colors.white)),
            Paragraph("<b>Exact Directional Speech (Word-for-Word What to Say)</b>", ParagraphStyle('Hdr2', parent=body_style, fontName='Helvetica-Bold', textColor=colors.white))
        ],
        [
            Paragraph("<b>[0:00 – 0:40]</b><br/><br/>"
                      "<b>OPEN ON SCREEN:</b><br/>"
                      "GitHub Repository page:<br/>"
                      "<code>github.com/MohammadZishanAlam/reviv-ai-l</code><br/><br/>"
                      "<b>POINT MOUSE TO:</b><br/>"
                      "Project Title & Badges.", cue_style),
            Paragraph('"Hi everyone, I’m Mohammad Zishan Alam, and this is <b>Reviv-AI-l</b>—an autonomous revenue recovery engine built for Track 3 of the Razorpay AI Buildathon.<br/><br/>'
                      'In Indian e-commerce, 15 to 25% of checkouts fail. The problem isn’t that customers don\'t want to buy—it\'s that they hit transient bank server downtime, daily UPI ceiling limits, or OTP friction.<br/><br/>'
                      'Today, merchants either do nothing, losing millions in GMV, or they use <i>dumb dunning</i>—spamming customers with immediate retry SMS links while the issuer bank is actively down, causing repeat failures and customer churn.<br/><br/>'
                      'I built Reviv-AI-l to solve this at the infrastructure level: intercepting Razorpay failure webhooks, diagnosing root cause with bank telemetry, and executing bounded recovery workflows that protect merchant reputation."', speech_style)
        ],
        [
            Paragraph("<b>[0:40 – 1:20]</b><br/><br/>"
                      "<b>SWITCH WINDOW TO:</b><br/>"
                      "Split Screen:<br/>"
                      "• <b>Left:</b> Terminal with uvicorn server running.<br/>"
                      "• <b>Right:</b> Browser at <code>http://localhost:8000</code>.<br/><br/>"
                      "<b>POINT MOUSE TO:</b><br/>"
                      "Terminal logs, then to the green '● Agent Active' badge.", cue_style),
            Paragraph('"Notice my screen setup: on the left is our FastAPI backend server, and on the right is the live Merchant Command Center connected via WebSockets.<br/><br/>'
                      'Before testing, let me highlight three critical engineering decisions I made in the backend:<br/>'
                      '1. <b>Cryptographic Security:</b> I implemented strict HMAC-SHA256 signature verification matching Razorpay’s exact spec. Tampered payloads are rejected with HTTP 400.<br/>'
                      '2. <b>Idempotency Gate:</b> Webhook delivery is at-least-once. I added atomic deduplication by transaction ID to prevent duplicate dunning links.<br/>'
                      '3. <b>Dual-Engine Failover:</b> External LLMs can time out. While we use Gemini 2.0 Flash for semantic reasoning, if the API experiences latency, the system automatically fails over in under 5 milliseconds to a deterministic heuristic rule engine."', speech_style)
        ],
        [
            Paragraph("<b>[1:20 – 2:10]</b><br/><br/>"
                      "<b>ACTION TO EXECUTE:</b><br/>"
                      "On the right panel, under 'Interactive Failure Simulator',<br/>"
                      "<b>CLICK:</b><br/>"
                      "<b>[Scenario A: SBI CBS Server Downtime]</b><br/><br/>"
                      "<b>POINT MOUSE TO:</b><br/>"
                      "1. Left terminal (shows incoming POST log).<br/>"
                      "2. Right card (shows 'Delay: 15m (Bank Down)').", cue_style),
            Paragraph('"Let’s test <b>Scenario A: SBI CBS Downtime</b>. Watch the terminal on the left as I click.<br/><br/>'
                      '<i>[Click Scenario A]</i><br/><br/>'
                      'Look at the terminal: it immediately ingested the <code>payment.failed</code> webhook and inspected SBI telemetry. Now look at the generated card on the right:<br/>'
                      'Notice the AI’s decision: it diagnosed the 504 gateway lag and enforced an <b>adaptive 15-minute retry delay</b>.<br/><br/>'
                      'It purposely does NOT dispatch immediately, because retrying right now would guarantee a second failure. It waits until the bank rail stabilizes."', speech_style)
        ],
        [
            Paragraph("<b>[2:10 – 3:00]</b><br/><br/>"
                      "<b>ACTION TO EXECUTE:</b><br/>"
                      "On the simulator panel,<br/>"
                      "<b>CLICK:</b><br/>"
                      "<b>[Scenario C: High-Cart OTP Dropoff]</b><br/><br/>"
                      "<b>THEN CLICK:</b><br/>"
                      "<b>[Preview Outreach]</b> button on the new card.<br/><br/>"
                      "<b>POINT MOUSE TO:</b><br/>"
                      "1. '+5.0% Incentive' badge.<br/>"
                      "2. WhatsApp modal with the dynamic link.", cue_style),
            Paragraph('"Now let’s test <b>Scenario C: High-Cart Friction</b> with an ₹8,999 order.<br/><br/>'
                      '<i>[Click Scenario C]</i><br/><br/>'
                      'The cart value is high, and the failure was OTP session friction. Notice the green badge on the card: the agent dynamically attached an authorized <b>5% recovery incentive</b> to close the sale.<br/><br/>'
                      'Let’s see what the buyer experiences: I will click <b>Preview Outreach</b>.<br/><br/>'
                      '<i>[Click Preview Outreach]</i><br/><br/>'
                      'This opens the exact WhatsApp message the customer receives with their personalized dynamic Razorpay checkout link.<br/>'
                      'Also note our <b>Stopping Rule</b>: if a card is stolen or blocked, the agent is hardcoded to abort dunning immediately to protect compliance."', speech_style)
        ],
        [
            Paragraph("<b>[3:00 – 3:30]</b><br/><br/>"
                      "<b>ACTION TO EXECUTE:</b><br/>"
                      "1. Click <b>[Done]</b> to close modal.<br/>"
                      "2. On the left panel, click:<br/>"
                      "<b>[Run 25-Record Batch Benchmark]</b><br/><br/>"
                      "<b>POINT MOUSE TO:</b><br/>"
                      "1. Batch Audit Modal pops up.<br/>"
                      "2. Total Rescued GMV & Recovery Rate.<br/>"
                      "3. Stopping Rules: 3 fraud stopped.<br/>"
                      "4. Bank Down: 8 delayed 15m.<br/>"
                      "5. SQLite Audit Trail verified.", cue_style),
            Paragraph('"Now, let\'s address the specific bar for Track 3: <i>Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail.</i><br/><br/>'
                      'Let’s click <b>Run 25-Record Batch Benchmark</b>.<br/><br/>'
                      '<i>[Click Batch Benchmark button]</i><br/><br/>'
                      'Look at the audit breakdown that just ran across 25 diverse transactions:<br/>'
                      '• <b>Measured Recovery:</b> Over ₹1.3 Lakhs in GMV recovered with a 70%+ recovery rate.<br/>'
                      '• <b>Stopping Rules:</b> 3 stolen/compromised cards were detected and halted with zero outreach.<br/>'
                      '• <b>Compliant Escalation:</b> 8 transactions on degraded bank rails were delayed 15 minutes to prevent spamming.<br/>'
                      '• <b>Audit Trail:</b> All 25 events are cryptographically recorded in our SQLite audit log."', speech_style)
        ],
        [
            Paragraph("<b>[3:30 – 4:00]</b><br/><br/>"
                      "<b>SWITCH WINDOW TO:</b><br/>"
                      "Terminal (Full Screen).<br/><br/>"
                      "<b>ACTION TO EXECUTE:</b><br/>"
                      "Run in terminal:<br/>"
                      "<code>.\\.venv\\Scripts\\python.exe -m pytest tests/ -v</code><br/><br/>"
                      "<b>POINT MOUSE TO:</b><br/>"
                      "9 passed in &lt;1.0s.", cue_style),
            Paragraph('"To conclude with <b>Failure Recovery and Build Quality</b>: during development on Windows, CLI runners faced a UnicodeEncodeError on CP1252 consoles. I resolved this by reconfiguring stdout in the Python runtime.<br/><br/>'
                      'Let’s run our automated test suite in the terminal:<br/><br/>'
                      '<i>[Run pytest command]</i><br/><br/>'
                      'All 9 tests pass in under one second—verifying HMAC verification, error classification, dynamic payment links, fraud stopping rules, and database integrity.<br/><br/>'
                      'The full IEEE 830 specification, CLI batch runner, and codebase are live on my GitHub repository. Thank you!"', speech_style)
        ]
    ]

    t_script = Table(script_data, colWidths=[155, 385])
    t_script.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 1, primary_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('BACKGROUND', (0,1), (0,-1), bg_light),
        ('BACKGROUND', (1,1), (1,-1), colors.white),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_script)

    doc.build(story)
    print(f"Enhanced PDF successfully generated at: {OUTPUT_PDF}")

if __name__ == "__main__":
    build_pdf()
