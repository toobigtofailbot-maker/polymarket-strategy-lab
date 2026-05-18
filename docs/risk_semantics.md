# Risk Semantics

## Terms

- Global exposure: total portfolio exposure across all strategies and markets.
- Strategy exposure: exposure attributable to one strategy module.
- Market exposure: exposure within one market.
- Correlated-event exposure: exposure across markets linked to the same or related event.
- Daily loss limit: maximum allowed realized and marked loss in one trading day.
- Max drawdown: maximum allowed decline from peak equity.
- Stale data kill-switch: disables decisions when data freshness requirements fail.
- API failure kill-switch: disables affected paths after API errors exceed limits.
- Failed order threshold: limit on failed order attempts before disablement.
- Failed arbitrage leg handling: deterministic response when one leg of a multi-leg trade fails.
- Wallet-copy caps: exposure, size, delay, and slippage limits for copy-trading.
- Market-making inventory limits: max inventory and skew bounds for quoting.
- Live-mode capital limit: maximum capital allocated to live trading.
- Strategy disablement: deterministic process for turning off a strategy after risk events.

## Initial Risk Posture

- Daily loss limit target: 10 percent of allocated live capital.
- Initial live capital range: 100-1,000 USD.
- Live trading disabled by default.
- Risk engine must be deterministic.
- AI and Hermes cannot override the risk engine.

