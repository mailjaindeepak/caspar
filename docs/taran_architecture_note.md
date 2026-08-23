# Taran's Architecture Note — LMS Wishlist (§7–§22)

Received from Taran Chhabra, Aug 2026 (after reviewing the Karnal prototype on Railway).
Sections §1–§6 were feedback on the existing prototype and are not reproduced here.
Sent alongside the Autograph Greater Noida West feasibility study (78-slide deck), which
several sections reference as the methodological model ("￼" marks in the original = citations to that deck).

Kept verbatim so future work can be traced back to the original ask.

---

## 7. Opportunity Architecture & Lead Prioritisation

The LMS should ideally work on opportunities rather than only companies/leads:

City → Micro-market → Developer → Land Parcel/Project → Decision Makers → Opportunity

One developer may have multiple projects/land parcels and therefore multiple opportunities. Developers should also be tagged as Native / Non-Native and Local / Regional / National. While non-native developers may receive higher prospecting priority, the system should continue capturing the entire developer universe.

A Caspar Opportunity Score can subsequently prioritise opportunities based on developer strength, parcel/project potential, market positioning, hospitality/BR potential, project stage, decision-maker accessibility, existing Caspar relationship, etc., with a manual override available to Taran/VK.

## 8. City & Micro-Market Intelligence Bank

For every shortlisted city, the LMS should progressively build a reusable Caspar Market Intelligence Bank covering:

Economy & demographics | Key industries/employment drivers | Existing & upcoming infrastructure | Connectivity | Residential corridors | Commercial/office hubs | Hospitality supply | Social infrastructure | Major demand generators | Key micro-markets.

This research should remain stored city-wise and be reusable for both business development and future client feasibility studies, instead of undertaking the same research afresh for every mandate. This reflects the regional/site analytical approach used in our feasibility study.

## 9. Developer & Verified Decision-Maker Intelligence

Each developer profile should contain company background, geographic presence, key projects, development segments, hospitality exposure and branded-residence experience.

Alongside this, we should create a person-level database for:

Promoter/Owner | Chairman | MD | CEO | Directors | Strategy/BD Head | Hospitality/Relevant Business Head

Each contact should capture mobile, email, LinkedIn/profile, source, verification status and last verification date, preferably categorised as Verified / Probable / Unverified.

## 10. Land Parcel / Project Intelligence

The existing Land Parcels section and satellite view can be expanded to capture:

Location/coordinates | Land area | Ownership/developer | Existing use | Development status | Access/frontage | Surrounding developments | Nearby premium/luxury projects | Hotels | Infrastructure | FAR/FSI/zoning wherever available | Source/date verified.

Most importantly, each parcel/project should have an initial Potential Caspar Solution classification:

Hotel | Branded Residences | Hotel + BR | Serviced Apartments | Villas/Resort | Mixed-use Hospitality | Further Study Required.

## 11. Residential, Premium & Luxury Market Search

The LMS should have structured research fields for:

Launches | Sales/absorption | Unsold inventory | Inventory overhang | Historical/current ₹/sq.ft. | Price growth/CAGR | Unit configurations | Unit sizes | Ticket sizes | Premium/luxury supply & absorption | Upcoming projects.

Importantly, Premium / Luxury / Ultra-Luxury should NOT have one fixed ticket-size definition across India. The thresholds should be city/micro-market specific and editable based on that particular market.

The feasibility study itself analyses supply-demand, pricing and premium/luxury depth before reaching its recommendations.

## 12. Competitor Project Database

Build a searchable database of relevant developments containing:

Developer | Project | Location | Acreage | Units | Floors | Configuration | Unit sizes | Launch price | Current price | Transaction price where available | Ticket size | Launch date | Sales/absorption | Amenities | Project status | Source.

This becomes reusable intelligence rather than rebuilding competitor sets for every feasibility assignment.

## 13. Branded Residences Benchmark Library

Separately create a permanent India-level BR database:

Project | City | Developer | Hospitality/Designer Brand | Operator | Standalone/Co-located | Units | Configurations | Sizes | Pricing | ₹/sq.ft. | Ticket size | Indicative branded premium | Absorption | Services | Amenities | CAM/maintenance | Brand/operator economics wherever known | Key learnings.

Our feasibility study already benchmarks multiple branded developments across India, so over time this should become structured Caspar proprietary data/IP rather than remain embedded only within individual reports.

## 14. Preliminary Branded Development Viability / Feasibility Snapshot

For shortlisted opportunities, the LMS should eventually be capable of producing an internal preliminary assessment containing:

Developer + Parcel/Project + Market Positioning + Luxury Market Depth + Hospitality Supply Gap + BR Competition + Indicative Development Format + Potential Brand Category + Opportunity Score + Key Risks + Recommended Next Action.

This can help us determine why Caspar should approach a particular developer before outreach begins.

## 15. Feasibility Readiness & Information-Gap Tracker

For each serious opportunity, introduce a Feasibility Readiness % showing what information is already available and what remains outstanding.

For example:

City research ✓ | Micro-market ✓ | Developer ✓ | Parcel ✓ | Competitors ✓ | BR benchmarks ✓ | Market pricing ✓ | Site-specific data pending | Developer programme pending | Land cost pending | Construction assumptions pending.

Every important data point should ideally also record:

Source | Date | Published/Developer Data/Primary Research/Caspar Estimate | Verified/Estimated | Last Updated.

This is important because our feasibility methodology itself distinguishes published information from consultant estimates and explicitly identifies unavailable data rather than presenting assumptions as facts.

## 16. Demand, Product-Mix & Pricing Engine – Later Phase

Once sufficient market data is accumulated, the LMS could subsequently assist Caspar in analysing:

Regional demand → Micro-market demand → Relevant Premium/Luxury demand → Potential subject-property capture → Expected absorption.

The feasibility study already follows a bottom-up demand methodology, narrowing broader market volumes to the demand a specific property can realistically capture.

The same module can ultimately help recommend:

Product type | Unit mix | Unit sizes | Indicative ticket size | Launch pricing | Branded premium | Sales velocity, with Conservative / Realistic / Optimistic scenarios.

## 17. Financial Feasibility – Future Phase

The architecture should keep provision for project-level inputs such as:

Land value/cost | Developable/saleable area | Construction cost | Other development costs | Brand fees | Pricing | Sales/absorption schedule | Revenue/GDV.

Eventually this could support cash flows, development margin, NPV/IRR, sensitivity and residual land value, depending upon the scope of the particular mandate. The existing feasibility study already extends into cost/revenue assumptions, cash flows and NPV.

This need not be developed immediately but the data architecture should accommodate it from the beginning.

## 18. Intelligence-Led Outreach & Communication

Rather than sending the same generic Caspar introduction to every lead, the system should identify the reason for approach first:

Land-led opportunity | Existing project suitable for branding | Non-native market entry | Hospitality opportunity | BR opportunity | Luxury-product enhancement | Existing relationship/referral.

Then:

Research → Prioritise → Verify Decision Maker → Personalised Intro → Taran/VK Approval → Send → Track → Follow-up.

This would make Caspar's outreach more advisory/intelligence-led rather than appearing as mass business-development communication.

## 19. Lead-to-Mandate & Brand Engagement Workflow

The earlier manual tracker should form the basis of the post-qualification/deal-management workflow.

Suggested journey:

Identified → Researching → Qualified → Contact Verified → Intro Sent → Follow-up → Response → Meeting → Site Visit → Opportunity → Proposal → Advisory Agreement → Mandate → Brand Shortlisting → Brands Offered → Brand Site Visit → LOI/Term Sheet → Definitive Agreement → Closed / On Hold / Lost.

At this stage the system should incorporate the detailed fields we were manually maintaining — developer/landowner, concerned person, brand segment, brands offered/selected, brand visits, brand commercial structure, Caspar commercials/fee, payments, site visits, IM, feasibility/DBR, proposal, advisory agreement, remarks, etc.

## 20. Taran/VK Management & Action Dashboard

The dashboard should give us a quick management view rather than requiring us to go through individual records:

Cities scanned | Developers mapped | Parcels/projects identified | Priority-A opportunities | Verified decision makers | Outreach sent | Responses | Meetings | Site visits | Proposals | Mandates | Brand engagements | Feasibilities underway | Conversion ratios.

Most importantly, there should be an "Action Required / Follow-ups Due" view showing what needs our attention immediately.

## 21. Caspar Website Re-engineering & Positioning

While re-engineering the website, the positioning should reflect the broader Caspar capability being developed through this exercise:

Market Intelligence → Development Strategy → Feasibility → Hospitality/Branded Residence Advisory → Brand Procurement/Engagement → Transaction & Execution Support.

The feasibility capability can be positioned as an important value-add/differentiator for Caspar, rather than Caspar being perceived merely as an intermediary between developers and brands.

## 22. Phased Development & City Replication

Rather than building every functionality and replicating across multiple cities simultaneously, we should first make one city the complete prototype.

Once the research structure, developer/parcel mapping, contact verification, scoring, market intelligence, feasibility inputs and outreach workflow are satisfactory, the same architecture can be replicated city by city.

The eventual objective should be that every new city adds to a continuously growing proprietary Caspar intelligence database, which supports both origination of mandates and delivery of feasibility/advisory assignments.
