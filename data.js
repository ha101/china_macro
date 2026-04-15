window.DASHBOARD_DATA = {
  sources: [
    {
      id: "nbs-releases",
      name: "NBS Latest Releases",
      owner: "National Bureau of Statistics",
      url: "https://www.stats.gov.cn/english/PressRelease/",
      type: "official",
      bestFor: ["Monthly activity", "Labor", "Energy", "Cross-checks"],
      note: "Best top-level entry point for activity, labor, property, CPI/PPI, PMI, and annual communique releases."
    },
    {
      id: "nbs-70city",
      name: "NBS 70-city housing prices",
      owner: "National Bureau of Statistics",
      url: "https://www.stats.gov.cn/english/PressRelease/202602/t20260213_1962622.html",
      type: "official",
      bestFor: ["Property prices", "Housing sentiment"],
      note: "Official release for new and existing home prices across 70 cities."
    },
    {
      id: "nbs-cpi",
      name: "NBS CPI / PPI releases",
      owner: "National Bureau of Statistics",
      url: "https://www.stats.gov.cn/english/PressRelease/202601/t20260112_1962292.html",
      type: "official",
      bestFor: ["Inflation", "Deflation", "Nominal growth"],
      note: "Primary official read for headline CPI, food, services, and producer prices."
    },
    {
      id: "nbs-pmi",
      name: "NBS PMI releases",
      owner: "National Bureau of Statistics",
      url: "https://www.stats.gov.cn/english/PressRelease/202604/t20260401_1962920.html",
      type: "official",
      bestFor: ["Manufacturing cycle", "Inventories", "Prices"],
      note: "Includes headline PMI and key sub-indices like new orders, export orders, inventories, and prices."
    },
    {
      id: "nbs-profits",
      name: "NBS industrial profits release",
      owner: "National Bureau of Statistics",
      url: "https://www.stats.gov.cn/english/PressRelease/202601/t20260128_1962394.html",
      type: "official",
      bestFor: ["Margins", "Receivables", "Inventory days", "Sector profits"],
      note: "One of the best free official windows into corporate cash flow and deflation stress."
    },
    {
      id: "nbs-communique",
      name: "NBS annual statistical communique",
      owner: "National Bureau of Statistics",
      url: "https://www.stats.gov.cn/english/PressRelease/202602/t20260228_1962661.html",
      type: "official",
      bestFor: ["Demographics", "Urbanization", "Strategic sectors"],
      note: "Useful for annual population, urbanization, industry output, and structural trend tables."
    },
    {
      id: "pboc-home",
      name: "PBOC data and policy releases",
      owner: "People's Bank of China",
      url: "https://www.pbc.gov.cn/en/3688006/index.html",
      type: "official",
      bestFor: ["TSF", "Loans", "M1/M2", "Policy rates", "LPR"],
      note: "Primary official source for credit, money aggregates, and policy settings."
    },
    {
      id: "pboc-mpr",
      name: "PBOC monetary policy report",
      owner: "People's Bank of China",
      url: "https://www.pbc.gov.cn/en/3688229/3688353/3688356/4756453/5099512/2023113010350373875.pdf",
      type: "official",
      bestFor: ["Credit transmission", "Policy framing"],
      note: "Helpful for interpreting credit impulse and the intended financing mix."
    },
    {
      id: "pboc-policy",
      name: "PBOC speeches and policy language",
      owner: "People's Bank of China",
      url: "https://www.pbc.gov.cn/en/3688110/3688175/2025080817533640398/index.html",
      type: "official",
      bestFor: ["Policy cycle", "Wording shifts"],
      note: "Useful for monitoring changes in central-bank rhetoric before the hard data moves."
    },
    {
      id: "safe-home",
      name: "SAFE data portal",
      owner: "State Administration of Foreign Exchange",
      url: "https://www.safe.gov.cn/en/index.html",
      type: "official",
      bestFor: ["FX reserves", "BOP", "External debt", "Capital flow context"],
      note: "Primary official source for reserves, balance of payments, and gross external debt."
    },
    {
      id: "gacc-stats",
      name: "GACC trade statistics",
      owner: "General Administration of Customs",
      url: "https://english.customs.gov.cn/Statistics/Statistics?ColumnId=1",
      type: "official",
      bestFor: ["Exports", "Imports", "Trade balance"],
      note: "Official top-level trade tables and monthly updates."
    },
    {
      id: "gacc-major",
      name: "GACC major imports & exports",
      owner: "General Administration of Customs",
      url: "https://english.customs.gov.cn/Statistics/Statistics?ColumnId=6",
      type: "official",
      bestFor: ["Commodity volumes", "IC imports", "Destination detail"],
      note: "Best free official detail for commodity and electronics trade composition."
    },
    {
      id: "hkex-connect",
      name: "HKEX Stock Connect statistics",
      owner: "Hong Kong Exchanges and Clearing",
      url: "https://www.hkex.com.hk/Mutual-Market/Stock-Connect/Statistics/Historical-Daily?sc_lang=en",
      type: "official",
      bestFor: ["Northbound flows", "Southbound flows", "Daily capital sentiment"],
      note: "Daily and historical Stock Connect flow data."
    },
    {
      id: "mof-home",
      name: "MOF budget data",
      owner: "Ministry of Finance",
      url: "https://www.mof.gov.cn/en/",
      type: "official",
      bestFor: ["Revenue", "Expenditure", "Fiscal stance"],
      note: "Official budget operations and government finance releases."
    },
    {
      id: "sse-scfi",
      name: "Shanghai Shipping Exchange / SCFI",
      owner: "Shanghai Shipping Exchange",
      url: "https://en.sse.net.cn/",
      type: "official",
      bestFor: ["Shipping rates", "External demand pulse"],
      note: "Shipping-rate stress gauge and freight-market context."
    },
    {
      id: "caict",
      name: "CAICT / MIIT-linked handset releases",
      owner: "CAICT / MIIT ecosystem",
      url: "https://www.caict.ac.cn/english/",
      type: "official",
      bestFor: ["Phone shipments", "Tech adoption"],
      note: "Useful for smartphone and 5G handset shipment updates."
    },
    {
      id: "yahoo-fx",
      name: "Yahoo Finance USD/CNY history",
      owner: "Yahoo Finance",
      url: "https://finance.yahoo.com/quote/CNY%3DX/history?p=CNY%3DX",
      type: "market",
      bestFor: ["USD/CNY history"],
      note: "Convenient free price history when you want a quick FX series pull."
    },
    {
      id: "tradingeconomics-bonds",
      name: "Trading Economics China bond yield pages",
      owner: "Trading Economics",
      url: "https://tradingeconomics.com/china/government-bond-yield",
      type: "market",
      bestFor: ["10-year yields", "China-US spread quick checks"],
      note: "A practical fallback for public bond-yield checks when you do not have a cleaner feed."
    }
  ],
  cycles: [
    {
      id: "property",
      name: "Property cycle",
      cadence: "Monthly",
      description:
        "Property remains the central balance-sheet channel, so prices, turnover, starts, completions, land appetite, and funding need to be read together rather than in isolation.",
      whatMatters: [
        "Prices shape household wealth effects and confidence.",
        "Sales usually lead starts, so turnover is the earliest stabilization signal.",
        "Starts versus completions shows whether developers are still shrinking or shifting toward delivery."
      ],
      sourceIds: ["nbs-70city", "nbs-releases", "pboc-home"],
      metrics: [
        { name: "70-city new home price index", cadence: "Monthly", tags: ["prices", "housing"], sourceIds: ["nbs-70city"], mvp: true },
        { name: "70-city existing home price index", cadence: "Monthly", tags: ["prices", "resale"], sourceIds: ["nbs-70city"] },
        { name: "Real estate investment", cadence: "Monthly", tags: ["investment", "construction"], sourceIds: ["nbs-releases"] },
        { name: "Property sales by floor area", cadence: "Monthly", tags: ["sales", "turnover"], sourceIds: ["nbs-releases"], mvp: true },
        { name: "Property sales by value", cadence: "Monthly", tags: ["sales", "nominal"], sourceIds: ["nbs-releases"] },
        { name: "Housing starts", cadence: "Monthly", tags: ["construction", "leading"], sourceIds: ["nbs-releases"], mvp: true },
        { name: "Construction under way", cadence: "Monthly", tags: ["pipeline", "supply"], sourceIds: ["nbs-releases"] },
        { name: "Completions", cadence: "Monthly", tags: ["delivery", "supply"], sourceIds: ["nbs-releases"], mvp: true },
        { name: "Land purchase area by developers", cadence: "Monthly", tags: ["land", "developer appetite"], sourceIds: ["nbs-releases"] },
        { name: "Funds available to developers", cadence: "Monthly", tags: ["funding", "liquidity"], sourceIds: ["nbs-releases"] },
        { name: "Household medium/long-term loans (mortgage proxy)", cadence: "Monthly", tags: ["mortgages", "credit"], sourceIds: ["pboc-home"] }
      ]
    },
    {
      id: "credit",
      name: "Credit cycle",
      cadence: "Monthly",
      description:
        "China’s macro swing factor is often the change in credit creation rather than the absolute level, especially when fiscal and housing stress are both present.",
      whatMatters: [
        "Credit impulse matters more than raw TSF levels.",
        "The split between households, corporates, and government funding shows where easing is landing.",
        "Mortgage weakness versus corporate capex or government bond issuance helps identify the real policy transmission channel."
      ],
      sourceIds: ["pboc-home", "pboc-mpr"],
      metrics: [
        { name: "TSF flow", cadence: "Monthly", tags: ["social financing", "credit impulse"], sourceIds: ["pboc-home"], mvp: true },
        { name: "TSF stock growth", cadence: "Monthly", tags: ["social financing", "stock"], sourceIds: ["pboc-home"] },
        { name: "New RMB loans", cadence: "Monthly", tags: ["bank lending"], sourceIds: ["pboc-home"], mvp: true },
        { name: "Household loans", cadence: "Monthly", tags: ["consumer", "households"], sourceIds: ["pboc-home"], mvp: true },
        { name: "Household medium/long-term loans", cadence: "Monthly", tags: ["mortgages", "households"], sourceIds: ["pboc-home"] },
        { name: "Corporate medium/long-term loans", cadence: "Monthly", tags: ["capex", "corporates"], sourceIds: ["pboc-home"] },
        { name: "Government bond financing within TSF", cadence: "Monthly", tags: ["fiscal", "government"], sourceIds: ["pboc-home"] },
        { name: "Trust loans", cadence: "Monthly", tags: ["shadow banking"], sourceIds: ["pboc-home"] },
        { name: "Entrusted loans", cadence: "Monthly", tags: ["shadow banking"], sourceIds: ["pboc-home"] },
        { name: "Bankers' acceptances", cadence: "Monthly", tags: ["trade finance"], sourceIds: ["pboc-home"] },
        { name: "M2 growth", cadence: "Monthly", tags: ["money supply"], sourceIds: ["pboc-home"], mvp: true },
        { name: "M1 growth", cadence: "Monthly", tags: ["money supply", "activity"], sourceIds: ["pboc-home"] },
        { name: "Credit impulse", cadence: "Quarterly", tags: ["social financing", "second derivative"], sourceIds: ["pboc-home", "nbs-releases"], mvp: true },
        { name: "Household debt-to-GDP", cadence: "Quarterly", tags: ["leverage", "households"], sourceIds: ["tradingeconomics-bonds"] },
        { name: "Corporate debt-to-GDP", cadence: "Quarterly", tags: ["leverage", "corporates"], sourceIds: ["tradingeconomics-bonds"] },
        { name: "Government debt-to-GDP", cadence: "Quarterly", tags: ["leverage", "government"], sourceIds: ["tradingeconomics-bonds"] },
        { name: "Total debt-to-GDP", cadence: "Quarterly", tags: ["leverage", "total"], sourceIds: ["tradingeconomics-bonds"], mvp: true },
        { name: "Real credit growth", cadence: "Monthly", tags: ["credit", "real", "deflated"], sourceIds: ["pboc-home", "nbs-releases"] }
      ]
    },
    {
      id: "policy",
      name: "Policy cycle",
      cadence: "Continuous",
      description:
        "In China, policy wording often moves first. The question is whether verbal support converts into actual easing in rates, liquidity, mortgages, and local-government financing.",
      whatMatters: [
        "Rhetorical shifts can lead the data by months.",
        "Short rates, LPR changes, and RRR moves reveal the mechanical easing stance.",
        "City-level housing measures matter because implementation is often decentralized."
      ],
      sourceIds: ["pboc-home", "pboc-policy", "nbs-releases"],
      metrics: [
        { name: "1-year LPR", cadence: "Monthly", tags: ["rates", "lending"], sourceIds: ["pboc-home"] },
        { name: "5-year LPR", cadence: "Monthly", tags: ["mortgages", "rates"], sourceIds: ["pboc-home"] },
        { name: "RRR changes", cadence: "Event-driven", tags: ["liquidity", "banking"], sourceIds: ["pboc-home"] },
        { name: "7-day reverse repo rate", cadence: "Daily", tags: ["short rates", "policy"], sourceIds: ["pboc-home"] },
        { name: "MLF rate", cadence: "Monthly", tags: ["policy rates"], sourceIds: ["pboc-home"] },
        { name: "1Y real interest rate", cadence: "Monthly", tags: ["rates", "real"], sourceIds: ["pboc-home", "nbs-cpi"], mvp: true },
        { name: "5Y real interest rate", cadence: "Monthly", tags: ["rates", "real", "mortgages"], sourceIds: ["pboc-home", "nbs-cpi"] },
        { name: "PBOC liquidity operations", cadence: "Daily", tags: ["OMO", "liquidity"], sourceIds: ["pboc-home"] },
        { name: "Politburo and State Council wording changes", cadence: "Event-driven", tags: ["guidance", "rhetoric"], sourceIds: ["pboc-policy"] },
        { name: "Major-city mortgage and purchase restriction changes", cadence: "Event-driven", tags: ["housing policy", "cities"], sourceIds: ["pboc-policy"] },
        { name: "Term spread (10Y-1Y)", cadence: "Daily", tags: ["yield curve", "spread", "leading indicator"], sourceIds: ["tradingeconomics-bonds"] }
      ]
    },
    {
      id: "deflation",
      name: "Deflation / reflation cycle",
      cadence: "Monthly / Quarterly",
      description:
        "China can post acceptable real growth while still suffering weak nominal growth. The real question is whether pricing power, margins, and nominal incomes are healing.",
      whatMatters: [
        "CPI alone can understate deflation pressure if PPI and the GDP deflator remain weak.",
        "Industrial margins help verify whether producer-price weakness is hurting cash flow.",
        "Nominal GDP versus real GDP is a clean quarterly check on reflation."
      ],
      sourceIds: ["nbs-cpi", "nbs-pmi", "nbs-profits", "nbs-releases"],
      metrics: [
        { name: "CPI headline", cadence: "Monthly", tags: ["inflation", "consumers"], sourceIds: ["nbs-cpi"], mvp: true },
        { name: "Core CPI", cadence: "Monthly", tags: ["inflation", "core"], sourceIds: ["nbs-cpi"] },
        { name: "Food CPI", cadence: "Monthly", tags: ["inflation", "food"], sourceIds: ["nbs-cpi"] },
        { name: "Services CPI", cadence: "Monthly", tags: ["inflation", "services"], sourceIds: ["nbs-cpi"] },
        { name: "PPI", cadence: "Monthly", tags: ["producer prices", "deflation"], sourceIds: ["nbs-cpi"], mvp: true },
        { name: "PMI input prices", cadence: "Monthly", tags: ["prices", "survey"], sourceIds: ["nbs-pmi"] },
        { name: "PMI output prices", cadence: "Monthly", tags: ["prices", "survey"], sourceIds: ["nbs-pmi"] },
        { name: "GDP deflator", cadence: "Quarterly", tags: ["nominal growth", "deflator"], sourceIds: ["nbs-releases"] },
        { name: "Nominal GDP growth", cadence: "Quarterly", tags: ["nominal growth"], sourceIds: ["nbs-releases"] },
        { name: "Real GDP growth", cadence: "Quarterly", tags: ["growth", "real"], sourceIds: ["nbs-releases"], mvp: true },
        { name: "Industrial profit margins", cadence: "Monthly", tags: ["margins", "profits"], sourceIds: ["nbs-profits"] },
        { name: "Consumption contribution to GDP growth", cadence: "Annual", tags: ["GDP", "expenditure", "consumption"], sourceIds: ["nbs-communique"] },
        { name: "Investment contribution to GDP growth", cadence: "Annual", tags: ["GDP", "expenditure", "investment"], sourceIds: ["nbs-communique"] },
        { name: "Net exports contribution to GDP growth", cadence: "Annual", tags: ["GDP", "expenditure", "trade"], sourceIds: ["nbs-communique"] },
        { name: "Services share of GDP", cadence: "Annual", tags: ["GDP", "structure", "services"], sourceIds: ["nbs-communique"] }
      ]
    },
    {
      id: "household",
      name: "Household confidence / balance-sheet cycle",
      cadence: "Monthly / Quarterly",
      description:
        "The household pulse is best read through spending, jobs, hours, deposits, loans, and housing turnover together rather than through headline retail sales alone.",
      whatMatters: [
        "Retail sales without improving labor conditions can be misleading.",
        "Rising deposits alongside weak medium/long-term borrowing often signals caution and prepayment behavior.",
        "Housing turnover remains a critical bridge between household confidence and balance sheets."
      ],
      sourceIds: ["nbs-releases", "pboc-home"],
      metrics: [
        { name: "Retail sales", cadence: "Monthly", tags: ["consumption"], sourceIds: ["nbs-releases"], mvp: true },
        { name: "Retail sales ex-autos", cadence: "Monthly", tags: ["consumption", "core"], sourceIds: ["nbs-releases"] },
        { name: "Online retail sales", cadence: "Monthly", tags: ["e-commerce"], sourceIds: ["nbs-releases"] },
        { name: "Catering revenue", cadence: "Monthly", tags: ["services", "mobility"], sourceIds: ["nbs-releases"] },
        { name: "Urban surveyed unemployment", cadence: "Monthly", tags: ["labor"], sourceIds: ["nbs-releases"] },
        { name: "31-city unemployment", cadence: "Monthly", tags: ["labor", "cities"], sourceIds: ["nbs-releases"] },
        { name: "Hours worked per week", cadence: "Monthly", tags: ["labor", "income"], sourceIds: ["nbs-releases"] },
        { name: "Household deposits", cadence: "Monthly", tags: ["savings", "households"], sourceIds: ["pboc-home"] },
        { name: "Household deposit growth", cadence: "Monthly", tags: ["savings", "precautionary"], sourceIds: ["pboc-home"] },
        { name: "Household loans", cadence: "Monthly", tags: ["credit", "households"], sourceIds: ["pboc-home"], mvp: true },
        { name: "Home prices and housing turnover", cadence: "Monthly", tags: ["wealth effect", "property"], sourceIds: ["nbs-70city", "nbs-releases"] },
        { name: "Real retail sales growth", cadence: "Monthly", tags: ["consumption", "real"], sourceIds: ["nbs-releases", "nbs-cpi"], mvp: true },
        { name: "Household savings rate", cadence: "Annual", tags: ["savings", "households"], sourceIds: ["nbs-communique"] }
      ]
    },
    {
      id: "inventory",
      name: "Inventory / manufacturing cycle",
      cadence: "Monthly",
      description:
        "This cycle tells you whether industrial activity is demand-led or just unwanted stock build. Survey orders, inventories, production, and profits need to be cross-checked together.",
      whatMatters: [
        "New orders minus finished-goods inventory is a fast restocking gauge.",
        "Accounts receivable and inventory days help distinguish healthy demand from forced shipments.",
        "Survey prices help identify whether the manufacturing rebound is nominally healthy."
      ],
      sourceIds: ["nbs-pmi", "nbs-releases", "nbs-profits"],
      metrics: [
        { name: "Official manufacturing PMI", cadence: "Monthly", tags: ["manufacturing", "survey"], sourceIds: ["nbs-pmi"], mvp: true },
        { name: "PMI new orders", cadence: "Monthly", tags: ["orders", "leading"], sourceIds: ["nbs-pmi"], mvp: true },
        { name: "PMI export orders", cadence: "Monthly", tags: ["trade", "survey"], sourceIds: ["nbs-pmi"], mvp: true },
        { name: "PMI output", cadence: "Monthly", tags: ["production", "survey"], sourceIds: ["nbs-pmi"] },
        { name: "PMI raw-material inventory", cadence: "Monthly", tags: ["inventory", "inputs"], sourceIds: ["nbs-pmi"] },
        { name: "PMI finished-goods inventory", cadence: "Monthly", tags: ["inventory", "outputs"], sourceIds: ["nbs-pmi"] },
        { name: "PMI input prices", cadence: "Monthly", tags: ["prices"], sourceIds: ["nbs-pmi"] },
        { name: "PMI output prices", cadence: "Monthly", tags: ["prices"], sourceIds: ["nbs-pmi"] },
        { name: "Industrial production", cadence: "Monthly", tags: ["production", "output"], sourceIds: ["nbs-releases"], mvp: true },
        { name: "Industrial enterprise finished-goods inventory", cadence: "Monthly", tags: ["inventory", "stocks"], sourceIds: ["nbs-profits"] },
        { name: "Accounts receivable", cadence: "Monthly", tags: ["cash flow", "working capital"], sourceIds: ["nbs-profits"] },
        { name: "Capacity utilization", cadence: "Quarterly", tags: ["utilization"], sourceIds: ["nbs-releases"] },
        { name: "Services value-added growth", cadence: "Annual", tags: ["services", "output", "GDP"], sourceIds: ["nbs-communique"] }
      ]
    },
    {
      id: "profits",
      name: "Industrial profit / corporate cash-flow cycle",
      cadence: "Monthly",
      description:
        "Margins, receivables, and inventory pressure often expose hidden deflation stress sooner than headline growth does.",
      whatMatters: [
        "PPI plus margins is one of the cleanest stress tests for the industrial sector.",
        "Receivables and collection periods show whether revenue is translating into cash.",
        "Sector profit dispersion reveals where overcapacity or price wars are deepest."
      ],
      sourceIds: ["nbs-profits"],
      metrics: [
        { name: "Industrial profits", cadence: "Monthly", tags: ["profits", "headline"], sourceIds: ["nbs-profits"], mvp: true },
        { name: "Business revenue", cadence: "Monthly", tags: ["sales"], sourceIds: ["nbs-profits"] },
        { name: "Operating costs", cadence: "Monthly", tags: ["costs"], sourceIds: ["nbs-profits"] },
        { name: "Profit margin / profit rate of revenue", cadence: "Monthly", tags: ["margins"], sourceIds: ["nbs-profits"] },
        { name: "Accounts receivable", cadence: "Monthly", tags: ["cash flow"], sourceIds: ["nbs-profits"] },
        { name: "Finished-goods inventory", cadence: "Monthly", tags: ["inventory"], sourceIds: ["nbs-profits"] },
        { name: "Asset-liability ratio", cadence: "Monthly", tags: ["leverage"], sourceIds: ["nbs-profits"] },
        { name: "Per-hundred-yuan costs", cadence: "Monthly", tags: ["cost efficiency"], sourceIds: ["nbs-profits"] },
        { name: "Collection period for receivables", cadence: "Monthly", tags: ["working capital"], sourceIds: ["nbs-profits"] },
        { name: "Sector profit breakdown", cadence: "Monthly", tags: ["sectoral", "dispersion"], sourceIds: ["nbs-profits"] },
        { name: "Private enterprise profit growth", cadence: "Monthly", tags: ["profits", "private"], sourceIds: ["nbs-profits"] },
        { name: "State-holding enterprise profit growth", cadence: "Monthly", tags: ["profits", "state-owned"], sourceIds: ["nbs-profits"] }
      ]
    },
    {
      id: "external",
      name: "External demand / terms-of-trade cycle",
      cadence: "Monthly / Weekly",
      description:
        "Trade needs both value and volume context. Commodity volumes, electronics imports, freight rates, and reserves help separate real demand from price noise. Tariff uncertainty can cause front-loading of shipments that flatters short-term figures.",
      whatMatters: [
        "Imports by value can mislead when commodity prices swing, so pair value with volume wherever possible.",
        "IC imports and industrial commodities often reveal the true industrial pulse earlier than headline trade balances do.",
        "Shipping rates and reserves provide useful context on external demand and confidence.",
        "Sharp export surges during tariff uncertainty often reflect front-loading rather than durable demand — watch for reversals in following months."
      ],
      sourceIds: ["gacc-stats", "gacc-major", "safe-home", "sse-scfi"],
      metrics: [
        { name: "Exports (goods, RMB)", cadence: "Monthly", tags: ["trade", "external demand"], sourceIds: ["gacc-stats"], mvp: true },
        { name: "Imports (goods, RMB)", cadence: "Monthly", tags: ["trade", "domestic demand"], sourceIds: ["gacc-stats"], mvp: true },
        { name: "Trade balance", cadence: "Monthly", tags: ["trade balance"], sourceIds: ["gacc-stats"] },
        { name: "Exports by destination", cadence: "Monthly", tags: ["geography", "trade"], sourceIds: ["gacc-major"] },
        { name: "Imports by commodity", cadence: "Monthly", tags: ["commodities", "trade"], sourceIds: ["gacc-major"] },
        { name: "Integrated-circuit imports", cadence: "Monthly", tags: ["technology", "imports"], sourceIds: ["gacc-major"] },
        { name: "Energy and metals import volumes", cadence: "Monthly", tags: ["oil", "iron ore", "copper"], sourceIds: ["gacc-major"] },
        { name: "SCFI / shipping freight index", cadence: "Weekly", tags: ["freight", "shipping"], sourceIds: ["sse-scfi"] },
        { name: "FX reserves", cadence: "Monthly", tags: ["reserves", "buffers"], sourceIds: ["safe-home"] },
        { name: "Current account", cadence: "Quarterly", tags: ["bop", "external"], sourceIds: ["safe-home"] },
        { name: "Financial account balance", cadence: "Quarterly", tags: ["bop", "capital"], sourceIds: ["safe-home"] },
        { name: "Errors and omissions", cadence: "Quarterly", tags: ["bop", "residual", "capital flight"], sourceIds: ["safe-home"] },
        { name: "Gross external debt", cadence: "Quarterly", tags: ["debt", "external"], sourceIds: ["safe-home"] },
        { name: "Current account as % of GDP", cadence: "Annual", tags: ["bop", "GDP ratio", "external"], sourceIds: ["safe-home", "nbs-releases"] },
        { name: "Terms of trade proxy", cadence: "Monthly", tags: ["trade prices", "terms of trade"], sourceIds: ["gacc-stats"] }
      ]
    },
    {
      id: "capacity",
      name: "Capacity / overinvestment cycle",
      cadence: "Monthly / Annual",
      description:
        "Output strength can coexist with poor profitability if capacity keeps expanding faster than demand. Pair volume growth with margins and sector prices.",
      whatMatters: [
        "Sector output without profit growth can signal overcapacity rather than healthy expansion.",
        "Manufacturing and high-tech investment show where policy and capital are being pushed.",
        "Capacity utilization and sector price trends help verify whether investment is creating returns."
      ],
      sourceIds: ["nbs-releases", "nbs-communique", "nbs-profits"],
      metrics: [
        { name: "Total fixed-asset investment", cadence: "Monthly", tags: ["FAI", "total"], sourceIds: ["nbs-releases"], mvp: true },
        { name: "Private fixed-asset investment", cadence: "Monthly", tags: ["FAI", "private"], sourceIds: ["nbs-releases"], mvp: true },
        { name: "State-owned fixed-asset investment", cadence: "Monthly", tags: ["FAI", "state-owned"], sourceIds: ["nbs-releases"] },
        { name: "Manufacturing fixed-asset investment", cadence: "Monthly", tags: ["FAI", "manufacturing"], sourceIds: ["nbs-releases"] },
        { name: "High-tech industry investment", cadence: "Monthly", tags: ["FAI", "high-tech"], sourceIds: ["nbs-releases", "nbs-communique"] },
        { name: "Technology-transformation investment", cadence: "Monthly", tags: ["capex", "upgrading"], sourceIds: ["nbs-releases"] },
        { name: "Industrial production by sector", cadence: "Monthly", tags: ["output", "sectoral"], sourceIds: ["nbs-releases"] },
        { name: "EV output", cadence: "Monthly", tags: ["EV", "strategic sectors"], sourceIds: ["nbs-releases", "nbs-communique"] },
        { name: "Solar-cell output", cadence: "Monthly", tags: ["solar", "strategic sectors"], sourceIds: ["nbs-releases", "nbs-communique"] },
        { name: "Integrated-circuit output", cadence: "Monthly", tags: ["semiconductors", "output"], sourceIds: ["nbs-releases", "nbs-communique"] },
        { name: "Steel, cement, glass, and chemicals output", cadence: "Monthly", tags: ["heavy industry"], sourceIds: ["nbs-releases"] },
        { name: "Industrial profits by sector", cadence: "Monthly", tags: ["profits", "sectoral"], sourceIds: ["nbs-profits"] },
        { name: "Capacity utilization", cadence: "Quarterly", tags: ["capacity"], sourceIds: ["nbs-releases"] }
      ]
    },
    {
      id: "demographics",
      name: "Demographic / urbanization cycle",
      cadence: "Annual / Quarterly",
      description:
        "Demographics matter for housing demand, labor supply, savings behavior, and the longer-run fiscal burden. These are slow-moving but structurally decisive signals.",
      whatMatters: [
        "Births and natural population growth frame the longer-run housing demand base.",
        "Urbanization and migrant-worker dynamics still matter for household formation and city-level demand.",
        "Working-age population share shapes labor supply and medium-term growth potential.",
        "The dependency ratio directly affects the savings rate, fiscal burden, and healthcare spend trajectory."
      ],
      sourceIds: ["nbs-communique", "nbs-releases"],
      metrics: [
        { name: "Total population", cadence: "Annual", tags: ["population"], sourceIds: ["nbs-communique"] },
        { name: "Births", cadence: "Annual", tags: ["demographics"], sourceIds: ["nbs-communique"] },
        { name: "Total fertility rate", cadence: "Annual", tags: ["demographics", "fertility"], sourceIds: ["nbs-communique"] },
        { name: "Deaths", cadence: "Annual", tags: ["demographics"], sourceIds: ["nbs-communique"] },
        { name: "Natural population growth", cadence: "Annual", tags: ["demographics"], sourceIds: ["nbs-communique"] },
        { name: "Working-age population share", cadence: "Annual", tags: ["labor supply"], sourceIds: ["nbs-communique"] },
        { name: "Dependency ratio", cadence: "Annual", tags: ["aging", "fiscal burden"], sourceIds: ["nbs-communique"] },
        { name: "Urbanization rate", cadence: "Annual", tags: ["urbanization"], sourceIds: ["nbs-communique"] },
        { name: "Urban permanent residents", cadence: "Annual", tags: ["urbanization"], sourceIds: ["nbs-communique"] },
        { name: "Migrant worker population", cadence: "Annual", tags: ["labor", "migration"], sourceIds: ["nbs-releases", "nbs-communique"] },
        { name: "Household formation proxies", cadence: "Quarterly", tags: ["housing demand"], sourceIds: ["nbs-releases"] },
        { name: "Age structure", cadence: "Annual", tags: ["aging"], sourceIds: ["nbs-communique"] }
      ]
    },
    {
      id: "capital",
      name: "Capital-flow / confidence cycle",
      cadence: "Daily / Weekly / Monthly",
      description:
        "This cycle shows whether easing is being welcomed or treated as a sign of stress. Markets, FX, reserves, and cross-border flows tell that story quickly.",
      whatMatters: [
        "USD/CNY plus reserves is a simple external-confidence cross-check.",
        "Northbound versus Southbound flow direction helps read onshore versus offshore sentiment.",
        "China yields and the China-US spread provide context on policy easing and capital pressure."
      ],
      sourceIds: ["safe-home", "hkex-connect", "yahoo-fx", "tradingeconomics-bonds"],
      metrics: [
        { name: "USD/CNY", cadence: "Daily", tags: ["FX", "confidence"], sourceIds: ["yahoo-fx"], mvp: true },
        { name: "Offshore CNH", cadence: "Daily", tags: ["FX", "offshore"], sourceIds: ["yahoo-fx"] },
        { name: "FX reserves", cadence: "Monthly", tags: ["reserves"], sourceIds: ["safe-home"], mvp: true },
        { name: "Balance of payments", cadence: "Quarterly", tags: ["BOP"], sourceIds: ["safe-home"] },
        { name: "Gross external debt", cadence: "Quarterly", tags: ["external debt"], sourceIds: ["safe-home"] },
        { name: "Northbound and Southbound Stock Connect net flows", cadence: "Daily", tags: ["equities", "cross-border"], sourceIds: ["hkex-connect"], mvp: true },
        { name: "Foreign holdings of onshore bonds and equities", cadence: "Monthly", tags: ["ownership", "flows"], sourceIds: ["safe-home"] },
        { name: "China 10-year sovereign yield", cadence: "Daily", tags: ["rates", "bonds"], sourceIds: ["tradingeconomics-bonds"] },
        { name: "China 1-year sovereign yield", cadence: "Daily", tags: ["rates", "short-term"], sourceIds: ["tradingeconomics-bonds"] },
        { name: "Term spread (10Y-1Y)", cadence: "Daily", tags: ["yield curve", "spread"], sourceIds: ["tradingeconomics-bonds"], mvp: true },
        { name: "China-US yield spread", cadence: "Daily", tags: ["rates", "spread"], sourceIds: ["tradingeconomics-bonds"] },
        { name: "CSI 300", cadence: "Daily", tags: ["equities", "onshore"], sourceIds: ["tradingeconomics-bonds"] },
        { name: "H-shares / Hang Seng China Enterprises", cadence: "Daily", tags: ["equities", "offshore"], sourceIds: ["tradingeconomics-bonds"] }
      ]
    },
    {
      id: "labor",
      name: "Labor / income cycle",
      cadence: "Monthly / Quarterly",
      description:
        "A durable consumer rebound needs labor support. Hours worked and migrant-worker trends can be more revealing than the headline unemployment rate alone.",
      whatMatters: [
        "Hours worked often turns before headline labor rates do.",
        "Migrant-worker and service-sector data help identify whether domestic demand is broadening.",
        "Income growth versus nominal GDP is a good reality check on household purchasing power."
      ],
      sourceIds: ["nbs-releases", "nbs-pmi", "nbs-communique"],
      metrics: [
        { name: "Urban surveyed unemployment", cadence: "Monthly", tags: ["labor"], sourceIds: ["nbs-releases"] },
        { name: "31-city unemployment", cadence: "Monthly", tags: ["labor", "cities"], sourceIds: ["nbs-releases"] },
        { name: "Hours worked per week", cadence: "Monthly", tags: ["labor", "hours"], sourceIds: ["nbs-releases"] },
        { name: "Migrant worker totals", cadence: "Quarterly", tags: ["migration", "labor"], sourceIds: ["nbs-releases", "nbs-communique"] },
        { name: "Average wage growth", cadence: "Quarterly", tags: ["income"], sourceIds: ["nbs-releases", "nbs-communique"] },
        { name: "Per capita disposable income growth", cadence: "Quarterly", tags: ["income", "households"], sourceIds: ["nbs-releases", "nbs-communique"], mvp: true },
        { name: "PMI employment sub-indices", cadence: "Monthly", tags: ["survey", "employment"], sourceIds: ["nbs-pmi"] },
        { name: "Service-sector activity", cadence: "Monthly", tags: ["services", "employment"], sourceIds: ["nbs-releases"] },
        { name: "Income growth versus nominal GDP", cadence: "Quarterly", tags: ["income", "nominal"], sourceIds: ["nbs-releases"] },
        { name: "Real disposable income growth", cadence: "Annual", tags: ["income", "real", "deflated"], sourceIds: ["nbs-communique", "nbs-cpi"] },
        { name: "Labor productivity (GDP per employed person)", cadence: "Annual", tags: ["productivity", "efficiency"], sourceIds: ["nbs-communique"] }
      ]
    },
    {
      id: "fiscal",
      name: "Fiscal / local-government cycle",
      cadence: "Monthly / Quarterly",
      description:
        "Local-government strain often shows up through land sales, special-bond issuance, and infrastructure acceleration before it becomes obvious in the headline deficit.",
      whatMatters: [
        "TSF government-bond financing is a quick read on fiscal support intensity.",
        "Land sales and infrastructure FAI are key stress and policy-transmission indicators for local governments.",
        "Official budget data often understates the full local-government financing picture, so proxies still matter."
      ],
      sourceIds: ["mof-home", "pboc-home", "nbs-releases"],
      metrics: [
        { name: "General public budget revenue", cadence: "Monthly", tags: ["budget", "revenue"], sourceIds: ["mof-home"] },
        { name: "General public budget expenditure", cadence: "Monthly", tags: ["budget", "spending"], sourceIds: ["mof-home"] },
        { name: "Tax revenue", cadence: "Monthly", tags: ["tax"], sourceIds: ["mof-home"] },
        { name: "Land-sales revenue", cadence: "Monthly", tags: ["land", "local government"], sourceIds: ["mof-home", "nbs-releases"] },
        { name: "Government bond financing within TSF", cadence: "Monthly", tags: ["TSF", "government"], sourceIds: ["pboc-home"] },
        { name: "Local-government special bond issuance", cadence: "Monthly", tags: ["special bonds"], sourceIds: ["mof-home"] },
        { name: "Broad fiscal deficit", cadence: "Quarterly", tags: ["deficit"], sourceIds: ["mof-home"] },
        { name: "Infrastructure fixed-asset investment", cadence: "Monthly", tags: ["infrastructure", "FAI"], sourceIds: ["nbs-releases"] },
        { name: "LGFV stress proxies", cadence: "Weekly", tags: ["LGFV", "spreads"], sourceIds: ["tradingeconomics-bonds"] },
        { name: "Local government debt outstanding", cadence: "Quarterly", tags: ["debt", "local government"], sourceIds: ["mof-home"] },
        { name: "Fiscal impulse", cadence: "Monthly", tags: ["fiscal", "second derivative", "deficit"], sourceIds: ["mof-home", "nbs-releases"], mvp: true }
      ]
    },
    {
      id: "technology",
      name: "Technology / sanctions / upgrading cycle",
      cadence: "Monthly / Annual",
      description:
        "This cycle measures whether China is deepening domestic substitution and sustaining strategic capex under external restrictions.",
      whatMatters: [
        "IC output versus IC imports is the simplest import-substitution check.",
        "High-tech investment and electronics profits help show whether the push is economically productive.",
        "Phone shipments add a practical demand-side read on the electronics ecosystem."
      ],
      sourceIds: ["gacc-major", "nbs-releases", "nbs-communique", "caict", "nbs-profits"],
      metrics: [
        { name: "Integrated-circuit output", cadence: "Monthly", tags: ["chips", "output"], sourceIds: ["nbs-releases", "nbs-communique"] },
        { name: "Integrated-circuit imports", cadence: "Monthly", tags: ["chips", "imports"], sourceIds: ["gacc-major"] },
        { name: "Integrated-circuit exports", cadence: "Monthly", tags: ["chips", "exports"], sourceIds: ["gacc-major"] },
        { name: "High-tech manufacturing investment", cadence: "Monthly", tags: ["high-tech", "investment"], sourceIds: ["nbs-releases", "nbs-communique"] },
        { name: "Technology-transformation investment", cadence: "Monthly", tags: ["upgrading", "capex"], sourceIds: ["nbs-releases"] },
        { name: "Electronics manufacturing profits", cadence: "Monthly", tags: ["profits", "electronics"], sourceIds: ["nbs-profits"] },
        { name: "Computer and communications equipment profit growth", cadence: "Monthly", tags: ["profits", "sectoral"], sourceIds: ["nbs-profits"] },
        { name: "Smartphone and 5G phone shipments", cadence: "Monthly", tags: ["phones", "demand"], sourceIds: ["caict"] },
        { name: "Exports of machinery and electronics", cadence: "Monthly", tags: ["exports", "electronics"], sourceIds: ["gacc-major"] },
        { name: "Semiconductor equipment imports", cadence: "Monthly", tags: ["equipment", "chips"], sourceIds: ["gacc-major"] }
      ]
    },
    {
      id: "shadow",
      name: "Shadow / alternative activity cycle",
      cadence: "Weekly / Monthly / Annual",
      description:
        "Alternative activity gauges help when headline GDP feels too smooth. Energy, freight, ports, pollution, and shipping often give a cleaner direction-of-travel signal.",
      whatMatters: [
        "Electricity and freight are still among the simplest activity cross-checks.",
        "Weekly market or shipping measures can pick up demand shifts before the monthly macro print arrives.",
        "Alternative signals work best as confirmation tools, not as standalone substitutes for the official macro releases."
      ],
      sourceIds: ["nbs-releases", "nbs-communique", "sse-scfi"],
      metrics: [
        { name: "Electricity generation", cadence: "Monthly", tags: ["energy", "activity"], sourceIds: ["nbs-releases"] },
        { name: "Thermal power output", cadence: "Monthly", tags: ["power", "industry"], sourceIds: ["nbs-releases"] },
        { name: "Rail freight", cadence: "Monthly", tags: ["transport", "activity"], sourceIds: ["nbs-releases", "nbs-communique"] },
        { name: "Freight traffic / ton-kilometers", cadence: "Monthly", tags: ["transport"], sourceIds: ["nbs-communique"] },
        { name: "Port throughput", cadence: "Monthly", tags: ["ports", "trade"], sourceIds: ["nbs-communique"] },
        { name: "Air pollution / NO2", cadence: "Weekly", tags: ["satellite", "alternative"], sourceIds: ["nbs-releases"] },
        { name: "Night lights", cadence: "Monthly", tags: ["satellite", "alternative"], sourceIds: ["nbs-releases"] },
        { name: "SCFI container rates", cadence: "Weekly", tags: ["shipping", "rates"], sourceIds: ["sse-scfi"] },
        { name: "Commodity production and spot prices", cadence: "Weekly", tags: ["commodities", "prices"], sourceIds: ["nbs-releases"] },
        { name: "Steel inventory / rebar prices", cadence: "Weekly", tags: ["steel", "construction"], sourceIds: ["tradingeconomics-bonds"] }
      ]
    }
  ]
};
