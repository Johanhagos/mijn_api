# VAT & Compliance Sources (snapshot)

Fetched: 2026-03-10T00:00:00Z (local snapshot performed by agent)

- European Commission — VAT rates and rules
  - URL: https://taxation-customs.ec.europa.eu/business/vat/eu-vat-rules-topic/vat-rates_en
  - Status: redirected and reachable. Source contains the EU table of VAT rates and guidance on application of VAT across Member States.

- OECD — Consumption taxes / International VAT-GST Guidelines
  - URL: https://www.oecd.org/tax/consumption/vat-gst/
  - Status: fetched successfully.
  - Excerpt: "Value added tax, or VAT, is a tax on final consumption, widely implemented as the main consumption tax worldwide... The International VAT/GST Guidelines... establish common principles for consistent VAT treatment of international transactions."
  - Key links: International VAT/GST Guidelines, VAT digital toolkits, Consumption Tax Trends reports.

- Belastingdienst (Netherlands) — VAT (moms/BTW) guidance
  - URL: https://www.belastingdienst.nl/wps/wcm/connect/bldcontenten/belastingdienst/enterprise/vat
  - Status: fetch failed to extract content (page may require JS or redirected). Please review manually: https://www.belastingdienst.nl/

- Skatteverket (Sweden) — Mom (VAT) guidance
  - URL: https://www.skatteverket.se/foretagochorganisationer/moms.4.76a43be412206334b89800013623.html
  - Status: fetch failed to extract content (page structure or encoding prevented extraction). Please review manually: https://www.skatteverket.se/

Notes & next steps
- Snapshot stored here for audit. For production updates, grant the agent access to a stable API or a curated list of machine-readable sources (CSV/JSON) or allow scheduled scraping from these authoritative pages.
- I can parse the EU table and update `vat_compliance.json` automatically if you want; confirm and I'll proceed.
- Consider adding `VAT_ADMIN_KEY` env var to protect updates (see `agent/router.py`).


