import React, { useEffect, useRef, memo } from 'react';

function TradingViewWidget({ symbol = "NASDAQ:NVDA" }) {
    const container = useRef();

    useEffect(() => {
        // Clear previous widget
        if (container.current) {
            container.current.innerHTML = "";
        }

        const script = document.createElement("script");
        script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
        script.type = "text/javascript";
        script.async = true;
        script.innerHTML = JSON.stringify({
            "autosize": true,
            "symbol": symbol,
            "interval": "D",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "enable_publishing": false,
            "allow_symbol_change": true, // User can change inside chart too
            "calendar": false,
            "support_host": "https://www.tradingview.com"
        });
        container.current.appendChild(script);
    }, [symbol]); // Re-run when symbol changes

    return (
        <div className="h-full w-full bg-pro-card rounded-xl border border-gray-700 overflow-hidden" style={{ minHeight: "500px" }}>
            <div className="tradingview-widget-container" ref={container} style={{ height: "100%", width: "100%" }}></div>
        </div>
    );
}

export default memo(TradingViewWidget);
