# Bitcoin (BTC‑USD) Fundamental Analysis Report  
**Date of Analysis:** 2026‑03‑25  

## 1. Overview  
Bitcoin (BTC) is the original and largest cryptocurrency by market capitalization. Unlike traditional equities, Bitcoin does not issue financial statements (balance sheet, income statement, cash flow) because it is a decentralized digital asset, not a corporation. Consequently, the standard fundamental tools (`get_balance_sheet`, `get_cashflow`, `get_income_statement`) return no data for the ticker **BTC‑USD**. The available fundamental data comes from market‑price based metrics, which are the primary drivers of Bitcoin’s valuation.

## 2. Key Market Data (as of 2026‑03‑25)  
| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Name** | Bitcoin USD | – |
| **Market Capitalization** | $1,427,568,590,848 (~$1.43 trillion) | Indicates the total dollar value of all Bitcoin in circulation. A market cap above $1 trillion places Bitcoin among the top global assets by value, comparable to large‑cap equities and gold. |
| **52‑Week High** | $126,198.07 | The peak price reached over the past year, showing the upper bound of recent investor enthusiasm and market liquidity. |
| **52‑Week Low** | $60,074.20 | The trough price over the past year, reflecting the lower bound during periods of risk‑off sentiment or macro‑economic stress. |
| **50‑Day Average Price** | $69,531.52 | Short‑term trend indicator; the current price relative to this average can signal near‑term momentum. |
| **200‑Day Average Price** | $92,792.98 | Long‑term trend indicator; often used to assess the primary bull/bear regime. |

## 3. Price Trend & Momentum Analysis  
- **Current Position vs. Averages:** As of the data timestamp, the 50‑day average ($69.5k) is *below* the 200‑day average ($92.8k), suggesting a **bearish crossover** (often termed a “death cross” in traditional technical analysis). This indicates that short‑term momentum has weakened relative to the longer‑term trend, potentially signaling further downside or consolidation.  
- **Range Bound Behavior:** The price is currently situated between the 52‑week low ($60k) and the 52‑week high ($126k). The proximity to the low end (current ~$69.5k vs. low $60k) suggests the asset is trading closer to its yearly trough than its peak, which may reflect subdued demand or accumulation phase.  
- **Volatility Implications:** The wide 52‑week range ($66k span) underscores Bitcoin’s inherent volatility. Traders should anticipate sharp price swings and employ risk‑management tools (e.g., stop‑losses, position sizing) appropriate for a high‑beta asset.  

## 4. Supply‑Side Fundamentals (Contextual, not from tool)  
While the tool does not provide on‑chain metrics, Bitcoin’s fundamental value is heavily influenced by its programmable supply:  
- **Fixed Supply Cap:** 21 million BTC, with approximately 19.5 million already mined (as of early 2026). The diminishing block subsidy (halving events) creates built‑in scarcity.  
- **Halving Schedule:** The most recent halving occurred in April 2024, reducing the block reward from 6.25 BTC to 3.125 BTC per block. The next halving is expected in 2028. Historically, halvings have preceded multi‑month bull runs, though past performance is not indicative of future results.  
- **Hash Rate & Security:** A robust and growing hash rate reflects miner confidence and network security, which indirectly supports price stability.  

## 5. Demand & Macro Drivers  
- **Institutional Adoption:** Growth in Bitcoin ETFs, custody solutions, and corporate treasury allocations continues to shape demand.  
- **Regulatory Environment:** Clarity (or lack thereof) in major jurisdictions (U.S., EU, Asia) significantly impacts investor sentiment.  
- **Macro Correlations:** Bitcoin often exhibits periods of correlation with risk assets (e.g., NASDAQ) and at times behaves as a “risk‑off” hedge similar to gold, depending on prevailing liquidity conditions.  

## 6. Risks & Considerations for Traders  
1. **Volatility:** Price swings of ±10% in a single day are not uncommon.  
2. **Liquidity Variability:** While spot markets are deep, futures and options liquidity can thin during extreme moves, leading to slippage.  
3. **Regulatory Shocks:** Sudden policy announcements (e.g., tax changes, trading bans) can trigger abrupt repricings.  
4. **Market Sentiment:** Bitcoin is heavily influenced by narratives, social media, and macro‑risk appetite, making sentiment‑based swings common.  

## 7. Conclusion  
Bitcoin’s fundamentals, as captured by market‑price based metrics, show a market capitalization of roughly $1.43 trillion, with the price trading below its 200‑day average but above its 52‑week low. The bearish crossover between the 50‑day and 200‑day averages suggests near‑term caution, while the long‑term scarcity narrative and ongoing institutional adoption provide a supportive backdrop. Traders should weigh the short‑term technical weakness against the longer‑term supply‑driven bullish case, employing strict risk controls given Bitcoin’s high volatility.

---

### Key Points Summary (Markdown Table)

| Metric | Value | Note |
|--------|-------|------|
| **Name** | Bitcoin USD | – |
| **Market Cap** | $1,427,568,590,848 | ~$1.43 trillion |
| **52‑Week High** | $126,198.07 | Annual peak |
| **52‑Week Low** | $60,074.20 | Annual trough |
| **50‑Day Average** | $69,531.52 | Short‑term trend |
| **200‑Day Average** | $92,792.98 | Long‑term trend |
| **Current Trend** | 50‑day < 200‑day (death cross) | Bearish short‑term momentum |
| **Price vs. 52‑Week Range** | Near lower end | Suggests possible accumulation or weak demand |

*All data sourced from `get_fundamentals` for BTC‑USD as of 2026‑03‑25.*