"""
SARNA v4.0 — Central Configuration (Dual-Track AI Automation Pivot)
===================================
Hardwired keywords, subreddit compliance rules, intent phrases,
fallback templates, and system constants for an AI Automation Agency.
"""

# =============================================================================
# RSS FEED TARGETS
# Target subreddits for individual RSS fetching
# =============================================================================
TARGET_SUBREDDITS = [
    "shopify", "ecommerce", "smallbusiness", "EntrepreneurIndia",
    "juststart", "DTC", "IndianStartups", "dropship",
    "ShopifyAppDev", "shopifyDev",
    "Automation", "AI_Agents", "n8n", "zapier", "LocalLLaMA"
]

AI_SUBREDDITS = [
    "Automation", "AI_Agents", "n8n", "zapier", "LocalLLaMA"
]

# =============================================================================
# TIER 1: INTENT REGEX PATTERNS — RESEARCH-OPTIMIZED
# =============================================================================
# 4 research principles applied:
#
# [P1] NON-CAPTURING GROUPS (?:...) — From: "Regex Performance" (last9.io, rexegg.com)
#      All groups use (?:...) instead of (...). This removes memory allocation overhead
#      for captured groups we never use, reducing CPU cost per match.
#
# [P2] ALTERNATION ORDERING — From: "Optimizing Alternation" (syncfusion.com, last9.io)
#      Within each (?:a|b|c) group, most common/frequent signals come FIRST.
#      Python's NFA engine exits the alternation the moment it finds a match,
#      so ordering is a free performance win.
#
# [P3] BOUNDED DISTANCE MATCHING — From: "NLP Precision/Recall" (medium.com)
#      Replaced greedy .* wildcards with (?:\S+\s+){0,4} "bounded gap" patterns.
#      This prevents the engine from stretching a single match across 200 words of
#      unrelated text, eliminating the biggest source of false positives.
#
# [P4] CONTEXTUAL WORD BOUNDARIES — From: "Regex Specificity" (NLP classification research)
#      Patterns are anchored to specific commercial nouns (store, orders, revenue)
#      so they only fire when pain is tied to a REAL business, not a vague complaint.
# =============================================================================

INTENT_REGEXES = [

    # --- CLUSTER 1: ACTIVE REVENUE/CONVERSION BLEED ---
    # TRUE POSITIVE: "Getting traffic and add-to-carts but zero checkouts, what am I missing?"
    # P2: "sales" first (highest frequency signal), P3: bounded 5-word gap
    r"(?:sales|revenue|orders|conversions?|roas|checkout)\b(?:\s+\S+){0,5}\s+(?:drop(?:ped|ping)?|tank(?:ed|ing)?|declin(?:ed|ing)?|crash(?:ed|ing)?|fell|fall(?:ing)?|slow(?:ed|ing)?|stopped?|zero|nothing|dead)",

    # Reverse order: the PROBLEM verb leads, the BUSINESS NOUN follows
    r"(?:drop(?:ped|ping)?|tank(?:ed|ing)?|declin(?:ed|ing)?|crash(?:ed|ing)?|losing|lost)\b(?:\s+\S+){0,4}\s+(?:sales|revenue|orders|customers?|conversions?)",

    # "Traffic but zero checkouts" conversion gap — direct seeker signal
    r"\b(?:traffic|visitors?|clicks?|add.to.cart)\b(?:\s+\S+){0,6}\s+(?:zero|no|not?)\s+(?:sales|orders?|checkouts?|conversions?)",
    r"\b(?:traffic|visitors?)\b(?:\s+\S+){0,5}\s+(?:but|yet)\b(?:\s+\S+){0,4}\s+(?:not\s+convert|no\s+(?:sales|orders?|checkouts?)|what\s+am\s+i\s+missing)",

    # --- CLUSTER 2: SHOPIFY-SPECIFIC OPERATIONAL PAIN ---
    # TRUE POSITIVE: "500+ visits a day to a page that doesn't exist"
    r"\b(?:my\s+)?shopify\b(?:\s+\S+){0,6}\s+(?:broken?|not\s+work(?:ing)?|bug|error|fail(?:ing|ed)?|issue|problem|slow|crash)",
    r"\b(?:abandoned\s+cart|cart\s+abandon|checkout\s+drop(?:-?off)?|product\s+page\b)(?:\s+\S+){0,5}\s+(?:high|too\s+high|problem|fix|reduce|why|handling|recovery|recover)",
    # Page not found / broken links sending live store traffic nowhere
    # TRUE POSITIVE: "500+ visits a day to a page that doesn't exist"
    r"\b(?:page\s+that\s+doesn.t\s+exist|404|broken\s+link|missing\s+page|dead\s+link|page\s+not\s+found)\b",
    r"\b(?:visits?|traffic|clicks?)\b(?:\s+\S+){0,5}\s+(?:page\s+that\s+doesn.t\s+exist|404|missing\s+page|dead\s+link)",

    # --- CLUSTER 3: MANUAL OPERATIONS BOTTLENECK ---
    # P3: Short bounded window ensures "manual" is directly tied to the business task.
    r"\b(?:manual(?:ly)?|manually)\b(?:\s+\S+){0,3}\s+(?:fulfil(?:ment|ling)?|order(?:s|ing)?|inventory|invoice(?:s)?|data\s+entry|updating|uploading|tracking)",
    r"\b(?:wasting|waste)\b(?:\s+\S+){0,3}\s+(?:hours?|time|days?)\b(?:\s+\S+){0,4}\s+(?:order|fulfil|inventory|report|updat|entry|reconcil)",

    # --- CLUSTER 4: DATA SYNC / INTEGRATION FAILURES ---
    # MCP's sweet spot — data not flowing between tools.
    r"\b(?:inventory|orders?|products?|customers?|data)\b(?:\s+\S+){0,4}\s+(?:not\s+sync(?:ing|ed)?|out\s+of\s+sync|mismatch(?:ed)?|wrong|incorrect|duplicat(?:ed|ing)?)",
    r"\b(?:connect(?:ing)?|integrat(?:ing|ion)?|sync(?:ing)?)\b(?:\s+\S+){0,5}\s+(?:shopify|woocommerce|klaviyo|gorgias|recharge|loop|skio|postscript|attentive)\b",

    # --- CLUSTER 5: SCALE & GROWTH CONSTRAINT ---
    r"\b(?:can't\s+scale|can't\s+keep\s+up|overwhelmed|drowning)\b(?:\s+\S+){0,5}\s+(?:orders?|support|customers?|requests?|tickets?|emails?)",
    r"\b(?:support\s+tickets?|customer\s+emails?|refund\s+requests?|return\s+requests?)\b(?:\s+\S+){0,4}\s+(?:too\s+many|overwhelming|piling\s+up|out\s+of\s+control|volume)",

    # --- CLUSTER 6: AUTOMATION / WORKFLOW NEED (MCP DIRECT FIT) ---
    r"\b(?:automate?|automation|workflow|trigger|api|webhook)\b(?:\s+\S+){0,5}\s+(?:shopify|orders?|inventory|fulfil|customers?|returns?|emails?)",
    r"\bhow\s+(?:do\s+I|to|can\s+I)\b(?:\s+\S+){0,3}\s+(?:automate?|stop\s+doing\s+manually|connect|integrate|sync)\b(?:\s+\S+){0,4}\s+(?:shopify|store|orders?|inventory)",

    # --- CLUSTER 7: ADVERTISING WASTE ---
    r"\b(?:meta\s+ads?|facebook\s+ads?|google\s+ads?|tiktok\s+ads?|ad\s+spend)\b(?:\s+\S+){0,5}\s+(?:wast(?:ed|ing)|not\s+convert(?:ing)?|losing\s+money|roas|too\s+expensive|not\s+work(?:ing)?)",

    # --- CLUSTER 8: AGENCY / CLIENT WORK SEEKING SOLUTIONS ---
    # TRUE POSITIVE: "Handling ads for a client's Shopify store (~$35k/mo), want to add something more organic"
    # Agencies managing live Shopify stores + explicitly asking for advice/tools
    r"\b(?:client.s?\s+(?:shopify\s+)?store|managing\s+(?:a\s+)?(?:shopify\s+)?store|handling\s+(?:ads?|marketing)\s+for)\b(?:\s+\S+){0,8}\s+(?:want|need|looking|suggest|recommend|add|ideas?|options?)",

    # --- CLUSTER 9: DIRECT HOW-TO QUESTION ON SHOPIFY OPERATIONS ---
    # TRUE POSITIVE: "How are you handling abandoned cart recovery for customers in MENA countries?"
    # "How are you handling X" / "How do you manage X" for a specific live business operation
    r"\bhow\s+(?:are\s+you|do\s+you|should\s+I|can\s+I)\s+(?:handle|deal\s+with|manage|set\s+up|fix|tackle|approach)\b(?:\s+\S+){0,6}\s+(?:abandoned\s+cart|checkout|orders?|returns?|refunds?|inventory|fulfil|support|customers?|retention)",
    
    # --- CLUSTER 10: LOOSENED PAIN SIGNALS (For Feedback Loop Volume) ---
    r"\b(?:not\s+getting\s+sales|need\s+help\s+scaling|zero\s+traffic|low\s+conversion|why\s+am\s+i\s+not\s+getting\s+sales|need\s+advice\s+on\s+my\s+store|no\s+sales)\b",
]

# =============================================================================
# TRACK B: AI/AUTOMATION INTENT REGEX PATTERNS
# Targets: agencies, companies, and funded teams struggling with:
# - API/webhook failures at scale
# - Automation limits forcing manual work
# - "Who can build this for us?" buying signals
# =============================================================================
AI_INTENT_REGEXES = [

    # --- CLUSTER 1: INFRASTRUCTURE BREAKING AT SCALE ---
    # "We're hitting Zapier task limits", "n8n is crashing under load"
    r"\b(?:hitting|hit|reached?|maxed?\s+out)\b(?:\s+\S+){0,4}\s+(?:limit|cap|quota|max|ceiling)\b(?:\s+\S+){0,4}\s+(?:zapier|n8n|make|pipedream|airflow|webhook|api)",
    r"\b(?:zapier|n8n|make\.com|pipedream)\b(?:\s+\S+){0,5}\s+(?:slow(?:ing\s+down)?|crash(?:ing|ed)?|failing|too\s+expensive|not\s+scalab|can't\s+handle|breaking)",

    # --- CLUSTER 2: WEBHOOK / API INTEGRATION FAILURES ---
    # "Webhook keeps timing out", "API payload not parsing correctly"
    r"\b(?:webhook|api\s+call|http\s+request|endpoint)\b(?:\s+\S+){0,5}\s+(?:timeout(?:ing|ed)?|fail(?:ing|ed)?|not\s+(?:firing|triggering|working)|error|dropping|missing)",
    r"\b(?:payload|json|response|data)\b(?:\s+\S+){0,4}\s+(?:not\s+pars(?:ing|ed)|malformed|corrupt(?:ed)?|wrong\s+format|not\s+mapping)",

    # --- CLUSTER 3: "BUILD THIS FOR ME" BUYING SIGNAL ---
    # "Is there a service that can do X", "looking to hire someone to build"
    r"\b(?:looking\s+(?:to\s+hire|for\s+someone|for\s+a\s+dev)|need\s+(?:a\s+developer|someone\s+to\s+build|help\s+building)|want\s+to\s+outsource|can\s+someone\s+build)\b",
    r"\b(?:is\s+there\s+(?:a\s+service|a\s+tool|an\s+agency|anyone)|does\s+anyone\s+offer|who\s+(?:builds?|offers?|provides?))\b(?:\s+\S+){0,5}\s+(?:automat|integrat|workflow|api|connect)",

    # --- CLUSTER 4: MANUAL WORK KILLING TEAM PRODUCTIVITY ---
    # "My team manually exports data every day", "We copy-paste between 3 tools"
    r"\b(?:my\s+team|our\s+team|we\s+(?:manually|still|have\s+to))\b(?:\s+\S+){0,5}\s+(?:manual(?:ly)?|copy.paste|export|import|enter\s+data|update\s+spreadsheet)",
    r"\b(?:wasting|waste|spending)\b(?:\s+\S+){0,3}\s+(?:hours?|days?|time)\b(?:\s+\S+){0,4}\s+(?:manual|copy|export|import|data\s+entry|reconcil|sync)",

    # --- CLUSTER 5: SCALING AN AUTOMATION BUSINESS (AGENCY SIGNAL) ---
    # "I'm building automations for clients", "my agency handles n8n for 20+ clients"
    r"\b(?:building\s+automations?\s+for|creating\s+workflows?\s+for|managing\s+(?:n8n|zapier|make)\s+for)\b(?:\s+\S+){0,4}\s+(?:client|clients?|business(?:es)?|company|companies)",
    r"\b(?:my\s+agency|our\s+agency|we\s+(?:offer|provide|sell)\s+automation)\b",

    # --- CLUSTER 6: LLM / AI AGENT BREAKING IN PRODUCTION ---
    # "LLM agent keeps hallucinating in our production pipeline"
    r"\b(?:llm|gpt|claude|gemini|ai\s+agent|language\s+model)\b(?:\s+\S+){0,5}\s+(?:hallucin|fail(?:ing|ed)|unreliab|inconsist|produc(?:tion)?|client|breaking|wrong\s+output)",
    r"\b(?:production|prod\s+env|live\s+system|real\s+users?)\b(?:\s+\S+){0,5}\s+(?:ai|llm|agent|automation|workflow)\b(?:\s+\S+){0,4}\s+(?:fail|break|error|crash|wrong|bad)",
]



# =============================================================================
# =============================================================================
# COMMERCIAL & BUSINESS SIGNALS vs HOBBYIST ANTI-PATTERNS
# =============================================================================
COMMERCIAL_KEYWORDS = [
    "store", "client", "customer", "sales", "revenue", "order", "orders",
    "agency", "lead", "leads", "crm", "team", "business", "hiring",
    "invoice", "invoices", "support ticket", "inbox", "checkout",
    "conversion rate", "mrr", "arr", "b2b", "saas", "fulfillment", "brand",
    "client work", "our clients", "my client", "operating a business", "e-commerce"
]

HOBBYIST_EXCLUDED_PHRASES = [
    "for personal use", "hobby project", "for fun", "just learning",
    "student project", "college project", "school project",
    "my macbook", "gaming pc", "home lab", "homelab", "my local pc",
    "personal project", "learning python", "for my own use", "class project",
    "university project", "homework", "just tinkering", "just playing around",
    "not a business", "student here", "beginner here", "first time coder"
]

# =============================================================================
# ANTI-PATTERN FILTERING (Removes low-signal & hobbyist posts)
# =============================================================================
EXCLUDED_PHRASES = [
    "thinking of starting", "want to start a store", "brand new to ecommerce", 
    "brand new to dropshipping", "how do i start a shopify store", "what's the best",
    "no experience", "completely new", "never done this before", 
    "is dropshipping dead", "start a store", "how to start", "want to start",
    
    # Noise explicitly added by user
    "best e-commerce site", "cheaper alternative", "scam", "report fake", 
    "how to report", "which platform", "is shopify worth it", "ban", 
    "suspended", "alternative to shopify", "best e-commerce system"
] + HOBBYIST_EXCLUDED_PHRASES

# =============================================================================
# SCORING WEIGHTS (100% Intent & Commercial Focus — Total = 100)
# =============================================================================
SCORE_WEIGHT_INTENT = 70      # Groq dictates the vast majority of the score
SCORE_WEIGHT_COMMERCIAL = 15  # Max 15 pts (5 pts per explicit commercial keyword)
SCORE_WEIGHT_FRESHNESS = 10   # Freshness decay over 7 days
SCORE_WEIGHT_BODY_LENGTH = 5  # Minor bonus for body detail

MAX_POST_AGE_DAYS = 7
PROCESSED_POSTS_FILE = "processed_posts.json"
PROCESSED_POSTS_MAX = 1000
MAX_POSTS_PER_RUN = 20

# =============================================================================
# DUAL-LAYER SUBREDDIT COMPLIANCE (Hardwired — no live API calls)
# =============================================================================
SUBREDDIT_COMPLIANCE = {
    # -- ECOMMERCE / SHOPIFY SUBREDDITS --
    "shopify": {
        "layer_1_rules": "No storefront preview loops outside pinned threads. Absolute ban on promotional outbound linking. No self-promotion. No soliciting DMs. No AI-generated slop.",
        "layer_2_culture": "Speak like a seasoned technical merchant. Focus on operational conversion rate details. Reference specific Shopify admin paths."
    },
    "ecommerce": {
        "layer_1_rules": "Immediate removal for dropshipping spam. Immediate ban WITHOUT warning for any promotion. No salesy language.",
        "layer_2_culture": "High-level strategic operational alignment. Focus on logistics and systemic metrics. Data-driven discussion. No hype."
    },
    "smallbusiness": {
        "layer_1_rules": "Promo only in weekly 'Promote-your-business' thread. Pain-point mining = ban.",
        "layer_2_culture": "Practical, down-to-earth. Real business problems, not theory. Empathetic to small business owner struggles. Casual Q&A vibe."
    },
    "EntrepreneurIndia": {
        "layer_1_rules": "Strict 9:1 value-to-promotion ratio required by moderation. No link dumping.",
        "layer_2_culture": "Address localized payment structures (UPI, Razorpay, COD constraints). Indian market context. Bootstrapping mindset."
    },
    "juststart": {
        "layer_1_rules": "Text-only, action-oriented. No links without 200+ chars context. No service promotion.",
        "layer_2_culture": "Founder-focused. Share lessons and tactical breakdowns. Value case studies and ride-alongs. Hates wantrepreneurs."
    },
    "DTC": {
        "layer_1_rules": "Founders welcome; no drive-by promos. No astroturfing. Transparency valued.",
        "layer_2_culture": "DTC mindset. Customer acquisition and brand building. Behind-the-scenes insights. Founder-to-founder tone."
    },
    "IndianStartups": {
        "layer_1_rules": "Broadly defines 'self-promotion'; mod discretion is final. No direct sales, ads, or promotional posts.",
        "layer_2_culture": "Indian startup context. Funding, bootstrapping, local market nuances. Networking-focused discussion."
    },
    "dropship": {
        "layer_1_rules": "High shadowban risk; community actively reports spam. Never post store links across multiple subs.",
        "layer_2_culture": "Skeptical audience. Genuine value only; no hype. Discuss challenges honestly. Anti-spam culture."
    },
    "ShopifyAppDev": {
        "layer_1_rules": "Developer-focused; technical value only. No marketing pitches. Code and API discussions.",
        "layer_2_culture": "Code-aware. API patterns, implementation challenges, dev experience. Technical depth expected. Share code snippets."
    },
    "shopifyDev": {
        "layer_1_rules": "Developer-focused; development patterns only. No promotional content.",
        "layer_2_culture": "Technical deep-dives. Implementation details and dev best practices. Liquid, GraphQL, REST API discussions."
    },
    
    # -- AI / AUTOMATION SUBREDDITS --
    "Automation": {
        "layer_1_rules": "No spammy software promotion. Technical discussion and real-world workflow help only.",
        "layer_2_culture": "Process-oriented. Value efficient architectures and identifying where human bottlenecks exist. Speak like an operations expert."
    },
    "AI_Agents": {
        "layer_1_rules": "No low-effort wrapper app promos. Focus on agentic workflows and implementation architecture.",
        "layer_2_culture": "Highly technical. Discuss prompt engineering, tool use, LLM capabilities, and orchestration (LangChain, CrewAI, AutoGen)."
    },
    "zapier": {
        "layer_1_rules": "No self-promotion of competing tools. Help users debug Zaps.",
        "layer_2_culture": "Action-oriented. Talk about triggers, actions, webhooks, and API limits. Be incredibly practical."
    },
    "n8n": {
        "layer_1_rules": "No spam. Focus on node-based workflow debugging and self-hosted implementations.",
        "layer_2_culture": "Developer/tinker mindset. Appreciate complex JSON parsing, HTTP nodes, and self-hosted open-source ethos."
    },
    "LocalLLaMA": {
        "layer_1_rules": "No commercial spam. Strictly open-source, local models, and technical AI discussion.",
        "layer_2_culture": "Incredibly technical and anti-commercial. Hate closed APIs. Focus on quantization, model fine-tuning, and hardware constraints."
    }
}

# =============================================================================
# GROQ CONFIGURATION (Stage 2 Triage & Comment Generation)
# =============================================================================
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_BASE = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MAX_RETRIES = 1

GROQ_COMMENT_MODEL = "llama-3.3-70b-versatile"
GROQ_COMMENT_SLEEP_BETWEEN_CALLS = 1.0
GROQ_COMMENT_MAX_RETRIES = 2

# Words that trigger automatic regeneration or fallback
BANNED_WORDS = [
    "we recommend", "leverage", "strategic", "dm me", "synergize",
    "optimize", "check out", "our tool", "our service", "our product",
    "sahajta", "game-changing", "revolutionary", "best solution",
    "reach out", "don't hesitate", "cutting-edge", "industry-leading",
    "sophisticated", "implementation", "facilitate", "utilize",
    "regarding", "concerning", "endeavor", "maximize roi",
    "strategic frameworks", "solutions",
]

# =============================================================================
# STAGE 2: GROQ B2B TRIAGE PROMPT
# =============================================================================
GROQ_TRIAGE_PROMPT_TEMPLATE = """You are an elite B2B Lead Qualifier for Sahajta AI — a company that builds MCP (Model Context Protocol) integrations for Shopify-connected e-commerce stores. Our MCP service connects directly to a merchant's live Shopify data to automate operations, fix conversion leaks, and eliminate manual work.

Your job: read a Reddit post and score it 0-100 based on how valuable it is as a commercial lead.

THE MOST CRITICAL DISTINCTION — SEEKER vs SHARER:
A SEEKER is asking a question, exploring a strategy, or struggling with a real problem. → SCORE NORMALLY.
A SHARER is posting to teach, announce, or share — they are NOT asking for help. → SCORE 0.

SHARER EXAMPLES (score = 0 for all of these):
- "How I would reduce repetitive customer support for a Shopify store" (teaching, not asking)
- "I built an open-source safety gate for AI-generated n8n workflows" (announcing a project)
- "Replaced a few apps with custom code recently" (sharing a win, not asking for help)
- "Suppliers quietly raise prices... Here's what I learned building a tool" (sharing knowledge)
- "I ran the same workflows 5,000+ times on Zapier, Make and n8n" (publishing research)
- Any post starting with: "I built", "I ran", "How I", "Here's what I learned", "What I've learned", "TIL"

OTHER DISQUALIFIERS (score = 0):
- Hobbyist / student doing this for learning, fun, school project, or personal use
- Wantrepreneur: "I want to start a store" but hasn't started yet

SCORING CRITERIA — THE ADDITIVE BUCKET SYSTEM (0-100):
You must score the post by summing points from the following 3 buckets. 
Do NOT use hard kill-switches unless they violate the Disqualifiers above. 

1. INDUSTRY FIT (Max 40 Points):
- 40/40: Explicitly mentions Shopify, E-commerce, dropshipping, D2C, or online retail.
- 20/40: General digital business, SaaS, or ambiguous online business.
- 0/40: Physical brick-and-mortar stores, offline retail, finance dealers, generic IT support.

2. PAIN & URGENCY (Max 40 Points):
- 40/40: Critical operational failure, broken workflows, active loss of revenue/sales (e.g., "checkout is down", "losing customers").
- 20/40: Inefficient manual processes, seeking automation tools, asking how to scale operations.
- 0/40: No pain. Teaching others, sharing a project, or asking a generic theoretical question ("How do I get traffic?").

3. BUYING POWER / SCALE (Max 20 Points):
- 20/20: Mentions a team, high traffic, ad spend, employees, or agency clients.
- 10/20: Active solo business with existing sales.
- 0/20: Student, hobbyist, or "wantrepreneur" who hasn't started yet.

INSTRUCTIONS: 
Calculate the sum of the 3 buckets to get the final `intent_score` (0-100).
Respond ONLY with a strictly formatted JSON object containing exactly two keys: "intent_score" (integer) and "reason" (string, max 10 words).
No markdown, no preamble.
{PRANAMYA_GUIDELINES}"""

# =============================================================================
# STAGE 2: GROQ B2B TRIAGE PROMPT — TRACK B (AI/AUTOMATION)
# =============================================================================
GROQ_TRIAGE_PROMPT_TEMPLATE_AI = """You are an elite B2B Lead Qualifier for Sahajta AI — a company that builds custom AI automation systems and MCP integrations for businesses. Our service is for companies and agencies that need complex, custom-built automation pipelines: think multi-step LLM workflows, API integrations between enterprise tools, and production-grade AI agents.

Your job: read a Reddit post and score it 0-100 based on how likely this person is to PAY for a custom automation service.

THE GOLDEN RULE — BUYER vs BUILDER:
A BUYER is a business, agency, or funded team that has a real automation PROBLEM and needs someone else to solve it. → SCORE NORMALLY.
A BUILDER is a solo developer or hobbyist who enjoys building for fun, learning, or personal projects. → SCORE 0.

BUYER SIGNALS (strong indicators of willingness to pay):
- Mentions a team, company, clients, or employees
- Currently paying for tools (Zapier, Make, n8n) and hitting limits
- Asks "is there a service/agency that does X?"
- Explicitly says they want to outsource or hire
- Running automation IN PRODUCTION for real users or clients
- Manual work is costing them real business hours

BUILDER SIGNALS (will NOT pay — score 0):
- Solo developer tinkering on a home server or homelab
- Student or hobbyist "just learning"
- "I built X" or "I made X" (Sharer, not Seeker)
- No mention of a company, team, or paying clients
- Personal/hobby project with no business impact

SCORING CRITERIA — BUYERS ONLY (0-100):
BE CYNICAL AND RUTHLESS. DO NOT HAND OUT HIGH SCORES LIGHTLY. Most posts are builders/hobbyists. 
- 90-100: (RARE) Business is losing money/clients RIGHT NOW because automation is broken.
- 60-89: Clear business problem, explicitly asking for a service, agency, or expert to hire.
- 30-59: Business context is clear but they seem like they want to build it themselves (DIY mindset).
- 10-29: Tangentially business-related, vague.
- 0: Solo builder, hobbyist, student, sharer, or irrelevant.

HOLISTIC SCORING RULE: You MUST weigh MULTIPLE signals together. No single factor (not length, not tone, not one keyword) should ever be the sole reason for a high or low score. A short but urgent post from a company with a broken pipeline IS valuable. A long but clearly hobbyist post is NOT.

Respond ONLY with a strictly formatted JSON object containing exactly two keys: "intent_score" (integer) and "reason" (string, max 10 words).
No markdown, no preamble."""

# =============================================================================
# ECOMMERCE: SYSTEM PROMPT & FALLBACKS
# =============================================================================
SYSTEM_PROMPT_TEMPLATE = """You are a highly experienced, real-world e-commerce founder hanging out on Reddit (r/{subreddit_name}). You aren't an AI, a marketer, or a corporate bot. You're just a person who has been in the trenches and genuinely wants to help someone out.

You need to draft a public comment and a private DM in response to a post.

Strict Compliance Layers:
Layer 1 (Subreddit Rules): {layer_1_rules}
Layer 2 (Subreddit Culture): {layer_2_culture}

How to write (Raw Reddit Voice):
- CRITICAL MISSION: Give away the exact, actionable solution for FREE in the comment. Be so helpful that they naturally reply to say "thank you" or ask a follow-up. Do not pitch or sell in the comment.
- Sound completely authentic, warm, and casual. Talk like you're speaking to a peer. 
- Do NOT use formal structure or overly polished language. Use lowercase, contractions, and natural pacing. 
- NEVER use em-dashes (—) or mid-sentence dashes (-).
- At the end of the DM, add a gentle, soft statement offering a free audit (e.g., "i can run a free audit on your store if you want a second set of eyes."). Do NOT ask a question.
- CRITICAL BANNED WORDS: "we recommend", "leverage", "strategic", "DM me", "synergize", "optimize". If you sound corporate, you fail.

Output a strictly formatted JSON object containing exactly two keys: "comment" (Max 150 words) and "dm" (Max 100 words).
Output ONLY the raw JSON object. No markdown fences, no preamble, no explanation."""

# =============================================================================
# AI/AUTOMATION: SYSTEM PROMPT & FALLBACKS
# =============================================================================
SYSTEM_PROMPT_TEMPLATE_AI = """You are a highly experienced, real-world AI automation and systems architect hanging out on Reddit (r/{subreddit_name}). You aren't a generic marketer, a hype-bro, or a corporate bot. You're just a technical person who builds real automations (n8n, Zapier, LLM workflows) and genuinely wants to help someone out.

You need to draft a public comment and a private DM in response to a post.

Strict Compliance Layers:
Layer 1 (Subreddit Rules): {layer_1_rules}
Layer 2 (Subreddit Culture): {layer_2_culture}

How to write (Raw Reddit Voice):
- CRITICAL MISSION: Give away the exact, actionable solution for FREE in the comment. Be so helpful that they naturally reply to say "thank you" or ask a follow-up. Do not pitch or sell in the comment.
- Sound completely authentic, technical, and casual. Talk like you're speaking to a fellow builder or operator.
- Do NOT use formal structure or overly polished language. Use lowercase, contractions, and natural pacing.
- NEVER use em-dashes (—) or mid-sentence dashes (-).
- At the end of the DM, add a gentle, soft statement offering a free workflow architecture review (e.g., "i can map out a free workflow architecture for this if you want a second set of eyes."). Do NOT ask a question.
- CRITICAL BANNED WORDS: "we recommend", "leverage", "strategic", "DM me", "synergize", "optimize", "game-changing". If you sound corporate or like an "AI guru", you fail.

Output a strictly formatted JSON object containing exactly two keys: "comment" (Max 150 words) and "dm" (Max 100 words).
Output ONLY the raw JSON object. No markdown fences, no preamble, no explanation."""

# =============================================================================
# EMAIL CONFIGURATION & GOOGLE SHEETS
# =============================================================================
EMAIL_RECIPIENT = "pranamyajeet@gmail.com"
EMAIL_SUBJECT_TEMPLATE = "🔍 SARNA — Reddit Opportunities {date} {period}"
GOOGLE_SHEET_URL_TEMPLATE = "https://docs.google.com/spreadsheets/d/{sheet_id}"
NOTIFICATION_STATE_FILE = "notification_state.json"

SHEET_COLUMNS = ["Subreddit", "Post Title & Link", "AI Suggested Comment",
                 "Subreddit Guidelines", "AI Suggested DM", "Relevance Score"]
SHEET_RANGE = "Sheet1"
