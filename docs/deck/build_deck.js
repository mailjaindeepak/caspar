const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625
pres.author = "Deepak Jain";
pres.title = "Caspar Intelligence & Lead System — Master Plan";

// ---- palette (matches the LMS app) ----
const NAVY = "1E2A44", NAVY2 = "1A2233", BLUE = "2E5FD0", BLUE_D = "2456C4";
const SLATE = "5B6A85", SLATE_L = "8593AD", LINE = "DDE3ED", CARD = "F5F7FA", WHITE = "FFFFFF";
const ICE = "C8D9FB";
const CHIP = {
  live:     { fill: "E8F6EE", text: "0D7A3F", label: "LIVE" },
  expand:   { fill: "E8F6EE", text: "0D7A3F", label: "LIVE · EXPANDING" },
  building: { fill: "FDF3DC", text: "8A5A09", label: "BUILDING" },
  next:     { fill: "E9F0FF", text: "2456C4", label: "NEXT" },
  later:    { fill: "EDF0F6", text: "5B6A85", label: "LATER" },
};
const FONT = "Calibri";
const shadow = () => ({ type: "outer", color: "000000", blur: 3, offset: 1, angle: 90, opacity: 0.10 });

// ---- helpers ----
function card(s, x, y, w, h, fill = CARD) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill }, line: { color: LINE, width: 0.75 }, rectRadius: 0.08, shadow: shadow() });
}
function chip(s, x, y, kind, w = 1.15) {
  const c = CHIP[kind];
  s.addText(c.label, { x, y, w, h: 0.26, shape: pres.ShapeType.roundRect, rectRadius: 0.13, fill: { color: c.fill },
    fontFace: FONT, fontSize: 8.5, bold: true, color: c.text, align: "center", valign: "middle", margin: 0, charSpacing: 0.5 });
}
function numCircle(s, x, y, n, d = 0.46, fill = NAVY) {
  s.addText(String(n), { x, y, w: d, h: d, shape: pres.ShapeType.ellipse, fill: { color: fill }, line: { color: fill },
    fontFace: FONT, fontSize: d > 0.4 ? 15 : 11, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
}
function footer(s, n, left) {
  if (left) s.addText(left, { x: 0.5, y: 5.22, w: 7.5, h: 0.25, fontFace: FONT, fontSize: 8.5, color: SLATE_L, margin: 0 });
  s.addText(String(n), { x: 9.0, y: 5.22, w: 0.5, h: 0.25, fontFace: FONT, fontSize: 8.5, color: SLATE_L, align: "right", margin: 0 });
}
function title(s, text, sub) {
  s.addText(text, { x: 0.5, y: 0.32, w: 8.0, h: 0.55, fontFace: FONT, fontSize: 24, bold: true, color: NAVY, margin: 0, valign: "middle" });
  if (sub) s.addText(sub, { x: 0.5, y: 0.88, w: 9.0, h: 0.35, fontFace: FONT, fontSize: 11.5, color: SLATE, margin: 0, valign: "top" });
}
// bullet list; items: string | {t, tag} | {h: "header"}
function bullets(s, x, y, w, h, items, fs = 10.5) {
  const runs = [];
  items.forEach((it, i) => {
    const last = i === items.length - 1;
    if (typeof it === "string") it = { t: it };
    if (it.h) {
      runs.push({ text: it.h, options: { bold: true, color: NAVY, fontSize: fs + 0.5, breakLine: true, paraSpaceBefore: i ? 5 : 0, paraSpaceAfter: 2 } });
      return;
    }
    // pptxgenjs writes one <a:pPr> per run and PowerPoint keeps the last, and a run without `bullet` emits <a:buNone/>.
    // So the tag run must carry the bullet too — and we give both runs the same `align` so pptxgenjs's
    // align-change check (which runs before its "bullet starts a new paragraph" rule) keeps them in one paragraph.
    runs.push({ text: it.t, options: { bullet: { indent: 12 }, align: "left", color: "2A3447", fontSize: fs, paraSpaceAfter: 3, breakLine: !it.tag } });
    if (it.tag) {
      const c = CHIP[it.tag];
      runs.push({ text: "  " + c.label.toLowerCase(), options: { bullet: { indent: 12 }, align: "left", color: c.text, fontSize: fs - 2, bold: true, paraSpaceAfter: 3, breakLine: true } });
    }
  });
  s.addText(runs, { x, y, w, h, fontFace: FONT, valign: "top", margin: 0 });
}
function stepSlide(n, total, heading, oneLiner, status, leftTitle, leftItems, rightTitle, rightItems, foot) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  numCircle(s, 0.5, 0.36, n);
  s.addText(heading, { x: 1.1, y: 0.32, w: 6.9, h: 0.55, fontFace: FONT, fontSize: 22, bold: true, color: NAVY, margin: 0, valign: "middle" });
  chip(s, 8.2, 0.47, status, 1.3);
  s.addText(oneLiner, { x: 1.1, y: 0.9, w: 8.4, h: 0.35, fontFace: FONT, fontSize: 11.5, color: SLATE, margin: 0 });
  // two cards
  card(s, 0.5, 1.4, 4.4, 3.65); card(s, 5.1, 1.4, 4.4, 3.65);
  s.addText(leftTitle, { x: 0.72, y: 1.52, w: 4.0, h: 0.32, fontFace: FONT, fontSize: 12.5, bold: true, color: BLUE_D, margin: 0 });
  s.addText(rightTitle, { x: 5.32, y: 1.52, w: 4.0, h: 0.32, fontFace: FONT, fontSize: 12.5, bold: true, color: BLUE_D, margin: 0 });
  bullets(s, 0.72, 1.9, 4.0, 3.05, leftItems, 11);
  bullets(s, 5.32, 1.9, 4.0, 3.05, rightItems, 11);
  footer(s, total, foot);
  return s;
}

// =====================================================================
// 1. TITLE
// =====================================================================
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addText("Caspar Intelligence & Lead System", { x: 0.7, y: 1.15, w: 8.6, h: 0.8, fontFace: FONT, fontSize: 34, bold: true, color: WHITE, margin: 0 });
  s.addText("Master plan of work — Karnal prototype to multi-city intelligence platform", { x: 0.7, y: 1.95, w: 8.6, h: 0.45, fontFace: FONT, fontSize: 15, color: ICE, margin: 0 });
  // six-step motif
  const steps = ["Leads", "Land parcels", "Developers", "Market", "Outreach &\nfeasibility", "LMS"];
  const x0 = 0.7, gap = 1.45;
  steps.forEach((t, i) => {
    const x = x0 + i * gap;
    numCircle(s, x, 3.0, i + 1, 0.5, BLUE);
    s.addText(t, { x: x - 0.35, y: 3.58, w: 1.2, h: 0.5, fontFace: FONT, fontSize: 10, color: ICE, align: "center", margin: 0, valign: "top" });
    if (i < steps.length - 1) s.addShape(pres.ShapeType.line, { x: x + 0.5, y: 3.25, w: gap - 0.5, h: 0, line: { color: "3A4C78", width: 1.25 } });
  });
  s.addText("Prepared for Varun Khanna & Taran Chhabra  ·  Caspar Wealth  ·  August 2026", { x: 0.7, y: 4.75, w: 8.6, h: 0.3, fontFace: FONT, fontSize: 11, color: "9DB0D8", margin: 0 });
  s.addText("Deepak Jain", { x: 0.7, y: 5.05, w: 8.6, h: 0.3, fontFace: FONT, fontSize: 11, color: "9DB0D8", margin: 0 });
}

// =====================================================================
// 2. WHERE WE ARE
// =====================================================================
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  title(s, "Where we are: the Karnal prototype is live", "Built and running since mid-August. Everything below refreshes automatically every Monday.");
  const tiles = [
    ["89", "leads under management"],
    ["9", "land parcels, licensed but unlaunched"],
    ["42", "hospitality CLUs with site status"],
    ["24", "licence applications in process"],
  ];
  tiles.forEach(([num, lab], i) => {
    const x = 0.5 + i * 2.3;
    card(s, x, 1.4, 2.1, 1.25);
    s.addText(num, { x: x + 0.15, y: 1.47, w: 1.8, h: 0.65, fontFace: FONT, fontSize: 34, bold: true, color: BLUE, margin: 0, valign: "middle" });
    s.addText(lab, { x: x + 0.15, y: 2.12, w: 1.85, h: 0.45, fontFace: FONT, fontSize: 10, color: SLATE, margin: 0, valign: "top" });
  });
  card(s, 0.5, 2.9, 5.85, 2.15);
  s.addText("Live in the prototype today", { x: 0.72, y: 3.0, w: 5.4, h: 0.3, fontFace: FONT, fontSize: 12.5, bold: true, color: BLUE_D, margin: 0 });
  bullets(s, 0.72, 3.35, 5.45, 1.65, [
    "Web app with admin/member roles, lead lanes with counts, statuses, notes and full audit trail",
    "Four lead lanes: land parcels · licence applications · hospitality CLUs · developers (14 scored)",
    "Satellite map with government parcel polygons; min-acreage and premiumness filters",
    "Weekly auto-refresh: DTCP licences + pending register, CLU permissions, HARERA, GIS",
    "Researched contacts with sources on 10 hospitality leads; dropped leads carry evidence",
  ], 10);
  card(s, 6.55, 2.9, 2.95, 2.15);
  s.addText("Prototype city", { x: 6.75, y: 3.0, w: 2.6, h: 0.3, fontFace: FONT, fontSize: 12.5, bold: true, color: BLUE_D, margin: 0 });
  s.addText([
    { text: "Karnal", options: { bold: true, fontSize: 16, color: NAVY, breakLine: true, paraSpaceAfter: 4 } },
    { text: "One city built end-to-end before replicating — the approach Taran's note sets out (§22).", options: { fontSize: 10, color: "2A3447", breakLine: true, paraSpaceAfter: 8 } },
    { text: "Demo", options: { bold: true, fontSize: 10, color: SLATE, breakLine: true } },
    { text: "web-production-350d.up.railway.app", options: { fontSize: 9.5, color: BLUE_D } },
  ], { x: 6.75, y: 3.35, w: 2.6, h: 1.65, fontFace: FONT, valign: "top", margin: 0 });
  footer(s, 2, "Figures as of 18 Aug 2026 weekly refresh");
  s.addNotes("Open with proof: the prototype exists, is used by the team, and refreshes itself. Lead counts from the 18 Aug refresh — check the live app before the meeting in case the Monday run has moved them.");
}

// =====================================================================
// 3. THE ENGINE
// =====================================================================
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  title(s, "The engine: six steps from raw records to a mandate", "Each step collects data, then decides something. Status shows what is live in Karnal today.");
  const steps = [
    ["Identify leads", "Government registers scanned weekly for new parcels, applications and CLUs", "live"],
    ["Grade land parcels", "Location, premiumness, surroundings → potential Caspar solution", "expand"],
    ["Grade developers", "Track record, native/non-native, verified decision-makers", "building"],
    ["Read the market", "City intelligence bank, luxury depth, competitors, BR benchmarks", "next"],
    ["Outreach & feasibility", "Approval-gated intros; feasibility snapshot → full study", "next"],
    ["Run the pipeline", "Lead-to-mandate workflow, team assignment, management dashboard", "expand"],
  ];
  const w = 1.32, gap = 0.216, y = 1.45, h = 2.75;
  steps.forEach(([t, d, st], i) => {
    const x = 0.5 + i * (w + gap);
    card(s, x, y, w, h);
    numCircle(s, x + 0.12, y + 0.14, i + 1, 0.4);
    s.addText(t, { x: x + 0.1, y: y + 0.62, w: w - 0.2, h: 0.5, fontFace: FONT, fontSize: 11.5, bold: true, color: NAVY, margin: 0, valign: "top" });
    s.addText(d, { x: x + 0.1, y: y + 1.12, w: w - 0.2, h: 1.15, fontFace: FONT, fontSize: 8.5, color: "2A3447", margin: 0, valign: "top" });
    chip(s, x + 0.08, y + h - 0.42, st, w - 0.16);
    if (i < steps.length - 1) s.addShape(pres.ShapeType.rightArrow, { x: x + w + 0.03, y: y + 1.2, w: gap - 0.06, h: 0.22, fill: { color: ICE }, line: { color: ICE } });
  });
  // legend
  const lg = [["live", "Running in Karnal"], ["building", "In progress now"], ["next", "Next 8 weeks"], ["later", "Later phase"]];
  lg.forEach(([k, t], i) => {
    const x = 0.5 + i * 2.3;
    chip(s, x, 4.5, k, 1.0);
    s.addText(t, { x: x + 1.08, y: 4.5, w: 1.2, h: 0.26, fontFace: FONT, fontSize: 9, color: SLATE, margin: 0, valign: "middle" });
  });
  footer(s, 3, "Structure follows Taran's note §7 (opportunity architecture) and §22 (one city, then replicate)");
}

// =====================================================================
// 4–9. STEP SLIDES
// =====================================================================
stepSlide(1, 4, "Identify leads", "Weekly scan of government registers; every lead enters the system with its source document attached.", "live",
  "What we collect  ·  weekly", [
    { h: "Government registers (DTCP, HARERA)" },
    "New CLU permissions for hospitality use",
    "Residential licences granted but not yet RERA-registered (unlaunched land)",
    "Licence applications in process — the earliest signal, before grant",
    "Rejected / lapsed applications — a re-approach pool",
    { h: "Launched projects in the city / micro-market" },
    { t: "Launch date, area, segment, launch price, unit size, stage, units sold, current price (RERA + web)", tag: "building" },
  ],
  "What the system decides", [
    "Which lane a lead belongs to: land parcel · application · hospitality · developer",
    "Whether a parcel is genuinely unlaunched — deterministic licence↔RERA citation match drops false positives",
    "What is new this week vs. already known — only genuinely new leads are added, nothing is overwritten",
    "Which team members can see it — cities are released to the team one at a time",
    { t: "Launched-project records feed the market layer in Step 4", tag: "next" },
  ],
  "Taran's note: §7 opportunity architecture · §22 prototype city   ·   Refresh: weekly (Mondays)");

stepSlide(2, 5, "Grade land parcels for branded collaboration", "Turn a licence number into a judged opportunity: where it is, how premium, and what Caspar could propose there.", "expand",
  "What we collect", [
    { h: "Parcel details  ·  government sources, weekly" },
    "Location & coordinates, parcel area, land use, developer, licence / CLU number, GIS polygon",
    { t: "FAR / FSI, zoning, access & frontage where available", tag: "next" },
    { h: "Location premiumness  ·  internet, monthly" },
    "Circle rates; surrounding premium / luxury projects; nearby hotels; infrastructure and connectivity",
    "Existing use and development status (vacant / under construction / operating)",
  ],
  "What the system decides", [
    "Premiumness of the locality and native / non-native developer flag (live)",
    { t: "Hospitality & BR potential — score 1 to 100", tag: "building" },
    { t: "Tier of potential hospitality partner", tag: "building" },
    { t: "Potential Caspar Solution: Hotel · Branded Residences · Hotel + BR · Serviced Apartments · Villas / Resort · Mixed-use · Further study required", tag: "building" },
    "Every field carries source and date verified (§15)",
  ],
  "Taran's note: §10 parcel intelligence · §7 · §15 provenance   ·   Refresh: weekly (parcels) / monthly (surroundings)");

stepSlide(3, 6, "Grade developers and verify decision-makers", "Who is behind the parcel, how capable they are, and whether we can actually reach the person who decides.", "building",
  "What we collect  ·  weekly", [
    { h: "Track record within the state  ·  government sources" },
    "Past projects: segment, area, launch rate & date, current rate, stage (launched → delivered)",
    { h: "Profile  ·  internet" },
    "Company background, geographic presence, hospitality exposure, branded-residence experience, news",
    { h: "Decision-makers  ·  person level" },
    "Promoter / Chairman / MD / CEO / Directors / Strategy-BD head / Hospitality head",
    "Mobile, email, LinkedIn, source, verification status and last-verified date",
  ],
  "What the system decides", [
    "Native vs. non-native; Local / Regional / National",
    "Hospitality and BR exposure (projects, partner brands, cities)",
    "Collaboration potential — score 1 to 100; new and non-native developers rank higher because a brand tie-up gives them the credibility they lack locally",
    "Competitor set for the developer's micro-market and city",
    "Contact confidence: Verified · Probable · Unverified",
    "Outreach-ready flag: scored, decision-maker verified, reason for approach identified",
  ],
  "Taran's note: §9 developer & decision-maker intelligence · §7 tags and opportunity score   ·   Refresh: weekly");

stepSlide(4, 7, "Read the city and micro-market", "A reusable intelligence bank per city — built once, used for both business development and every later feasibility mandate.", "next",
  "What we collect", [
    { h: "City intelligence bank  ·  per city, reusable" },
    "Economy & demographics, industry / employment drivers, infrastructure & connectivity, residential corridors, commercial hubs, hospitality supply, social infrastructure, demand generators, key micro-markets",
    { h: "Premium / luxury residential research" },
    "Launches, units, sizes, ticket sizes, units sold, unsold inventory, current price, price CAGR, upcoming projects",
    { h: "Two permanent libraries" },
    "Competitor project database (developer, project, acreage, units, pricing, absorption, status, source)",
    "India branded-residences benchmark library — seeded from Caspar's own studies",
  ],
  "What the system decides", [
    "Premium / Luxury / Ultra-luxury thresholds set per city and micro-market — editable, never one India-wide number",
    "Luxury market depth in the micro-market and city",
    "Hospitality supply gap",
    "Branded-residences competition and indicative branded premium",
    "Opportunity ranking within the city — which parcels and developers deserve an approach first",
  ],
  "Taran's note: §8 intelligence bank · §11 market fields · §12 competitor DB · §13 BR library   ·   Refresh: monthly / per mandate");

stepSlide(5, 8, "Outreach and feasibility", "Every approach starts from a reason, goes out only after approval, and is backed by a preliminary assessment.", "next",
  "Intelligence-led outreach", [
    { h: "Reason for approach, identified first" },
    "Land-led · existing project suitable for branding · non-native market entry · hospitality · branded residences · luxury-product enhancement · relationship / referral",
    { h: "Workflow" },
    "Research → prioritise → verify decision-maker → personalised intro drafted by the system → Taran / VK approval → send → track → follow-up",
    "Nothing goes out without approval; every touch is logged against the opportunity",
  ],
  "Feasibility, in two stages", [
    { h: "Preliminary snapshot  ·  per shortlisted opportunity" },
    "Developer + parcel + market positioning + luxury depth + hospitality supply gap + BR competition + indicative format + potential brand category + opportunity score + key risks + recommended next action",
    "Feasibility readiness % and information-gap tracker; every data point tagged published / developer data / primary research / Caspar estimate",
    { h: "Full study" },
    { t: "Demand model, product mix & pricing (conservative / realistic / optimistic), cash flows, NPV / IRR, residual land value — schema provisioned now, built later", tag: "later" },
  ],
  "Taran's note: §14 feasibility snapshot · §15 readiness & provenance · §16–§17 engines (later) · §18 intelligence-led outreach");

stepSlide(6, 9, "Run the pipeline: LMS and management view", "The system the team already works in, extended to carry each opportunity from first sighting to mandate.", "expand",
  "Live today", [
    "Lead lanes with counts; per-lane tables with filters, satellite map, parcel detail",
    "Statuses: new → researching → contacted → meeting → handed off → deal / dropped",
    "Notes, audit trail, dropped-lead evidence",
    "Admin / member roles; city-by-city release to the team",
    "Weekly sync adds new leads without touching team work",
  ],
  "Expanding", [
    { t: "Full lifecycle: Identified → Researching → Qualified → Contact verified → Intro sent → Follow-up → Response → Meeting → Site visit → Opportunity → Proposal → Advisory agreement → Mandate → Brand shortlisting → Brands offered → Brand site visit → LOI / term sheet → Definitive agreement → Closed / On hold / Lost", tag: "building" },
    { t: "Deal fields from the manual tracker: brands offered / selected, commercial structure, Caspar fee, payments, site visits, IM, feasibility / DBR, proposal, remarks", tag: "building" },
    { t: "Opportunity score with manual override; lead assignment to team", tag: "building" },
    { t: "Management dashboard — funnel counts, conversion ratios, and an Action Required / Follow-ups Due view", tag: "next" },
  ],
  "Taran's note: §7 opportunity score · §19 lead-to-mandate workflow · §20 management dashboard");

// =====================================================================
// 10. TARAN'S NOTE → PLAN
// =====================================================================
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  title(s, "Taran's architecture note, mapped to the plan", "Every section of §7–§22 has a home in the six steps and a phase.");
  const hdr = ["§", "Ask", "Lands in", "Phase"].map(t => ({ text: t, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 9 } }));
  const rows = [
    ["7", "Opportunity model, developer tags, Opportunity Score with manual override", "Steps 3 & 6", "Phase 1"],
    ["8", "City & micro-market intelligence bank", "Step 4", "Phase 2"],
    ["9", "Developer profiles + person-level verified decision-makers", "Step 3", "Phase 1 (sprint)"],
    ["10", "Parcel intelligence + Potential Caspar Solution", "Step 2", "Phase 1"],
    ["11", "Premium / luxury market fields; city-specific thresholds", "Step 4", "Phase 2"],
    ["12", "Competitor project database", "Step 4", "Phase 2"],
    ["13", "India branded-residences benchmark library", "Step 4", "Phase 2 · seed: Autograph study"],
    ["14", "Preliminary feasibility snapshot", "Step 5", "Phase 2"],
    ["15", "Feasibility readiness % and provenance on every data point", "Steps 2–5", "Phase 1 fields; Phase 2 roll-up"],
    ["16", "Demand, product-mix & pricing engine", "Step 5", "Phase 3"],
    ["17", "Financial feasibility (cash flows, NPV / IRR)", "Step 5", "Phase 3 — schema now"],
    ["18", "Intelligence-led, approval-gated outreach", "Step 5", "Phase 2"],
    ["19", "Lead-to-mandate workflow with deal fields", "Step 6", "Phase 1"],
    ["20", "Management dashboard + Action Required view", "Step 6", "Phase 1"],
    ["21", "Website re-engineering & positioning", "Separate track", "Parallel"],
    ["22", "One city as complete prototype, then replicate", "Karnal → city 2 → …", "All phases"],
  ].map((r, i) => r.map((c, j) => ({ text: c, options: { fontSize: 8.5, color: j === 0 ? NAVY : "2A3447", bold: j === 0, fill: { color: i % 2 ? WHITE : CARD } } })));
  s.addTable([hdr, ...rows], { x: 0.5, y: 1.28, w: 9.0, colW: [0.38, 5.05, 1.45, 2.12], fontFace: FONT, rowH: 0.222, border: { type: "solid", color: LINE, pt: 0.5 }, valign: "middle", margin: [0, 0.06, 0, 0.06] });
  footer(s, 10, "Full text of the note kept in the project repository (docs/taran_architecture_note.md)");
}

// =====================================================================
// 11. PHASES & NEXT 60 DAYS
// =====================================================================
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  title(s, "Phases and the next 60 days", "Finish one city properly, add the market layer with a second city, then build the engines on top of real data.");
  const phases = [
    ["Phase 1", "Weeks 1–4", "Karnal complete", "building", [
      "Developer tags: native / non-native, local / regional / national",
      "Potential Caspar Solution on every parcel",
      "Full lead-to-mandate lifecycle + deal fields",
      "Source / date / verified on every contact and fact",
      "Verified-contact sprint on the top 20 developers",
      "Management dashboard + Action Required view",
    ]],
    ["Phase 2", "Weeks 5–8", "Market layer + second city", "next", [
      "City intelligence bank (Karnal first)",
      "Premium / luxury research + city-specific thresholds",
      "Competitor project DB; BR benchmark library seeded",
      "Feasibility snapshot + readiness %",
      "Approval-gated outreach workflow",
      "Replicate the whole structure to city 2",
    ]],
    ["Phase 3", "Later", "Engines and scale", "later", [
      "Demand, product-mix & pricing engine",
      "Financial feasibility: cash flows, NPV / IRR, residual land value",
      "City-by-city roll-out across the target footprint",
      "Each new city adds to a proprietary Caspar intelligence base",
    ]],
  ];
  phases.forEach(([ph, wk, t, st, items], i) => {
    const x = 0.5 + i * 3.07, w = 2.86, y = 1.32, h = 2.72;
    card(s, x, y, w, h);
    s.addText(ph, { x: x + 0.18, y: y + 0.12, w: 1.2, h: 0.3, fontFace: FONT, fontSize: 14, bold: true, color: NAVY, margin: 0 });
    chip(s, x + w - 1.08, y + 0.14, st, 0.9);
    s.addText(wk + "  ·  " + t, { x: x + 0.18, y: y + 0.45, w: w - 0.36, h: 0.3, fontFace: FONT, fontSize: 10, color: SLATE, margin: 0 });
    bullets(s, x + 0.18, y + 0.82, w - 0.36, h - 0.9, items, 9.5);
  });
  card(s, 0.5, 4.22, 9.0, 0.85, "EEF1F7");
  s.addText("Decisions needed from Varun & Taran", { x: 0.72, y: 4.3, w: 4, h: 0.26, fontFace: FONT, fontSize: 11, bold: true, color: NAVY, margin: 0 });
  bullets(s, 0.72, 4.58, 4.2, 0.48, ["Confirm Karnal as the prototype city; choose city 2", "Who approves outreach drafts, and the turnaround we commit to"], 9.5);
  bullets(s, 5.1, 4.58, 4.2, 0.48, ["Priority developers for the verified-contact sprint", "Budget for contact-verification and data tools"], 9.5);
  footer(s, 11, "");
  s.addNotes("Close on the asks. Phase 1 is deliberately small and visible: each item makes the demo reflect Taran's note within a month.");
}

const out = process.argv[2] || "Caspar_LMS_Master_Plan.pptx";
pres.writeFile({ fileName: out }).then(f => console.log("wrote", f));
