// frontend/static/script.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("Script loaded and DOM content loaded.");

    // List of instruments to subscribe to (must match FastAPI's INSTRUMENTS_TO_SUBSCRIBE)
    const instrumentsToSubscribe = [
        "BTC_USD", "ETH_USD", "XRP_USD", "LTC_USD", "BCH_USD", "SOL_USD", "ADA_USD",
        "AVAX_USD", "DOT_USD", "DOGE_USD", "MATIC_USD", "SHIB_USD", "LINK_USD", "XLM_USD",
        "TRX_USD", "NEAR_USD", "ETC_USD", "FIL_USD", "APT_USD", "ARB_USD", "SUI_USD",
        "INJ_USD", "OP_USD", "PEPE_USD", "FTM_USD", "ALGO_USD", "GRT_USD", "IMX_USD",
        "AAVE_USD", "SNX_USD"
    ];

    const marketDataDisplay = document.getElementById('market-data-display');
    marketDataDisplay.innerHTML = ''; // Clear initial loading message

    // Object to hold WebSocket connections
    const activeWebsockets = {};

    // Function to create or update an order book display for a single instrument
    function updateOrderBookDisplay(data) {
        const instrumentId = data.instrument_id;
        let instrumentContainer = document.getElementById(`book-${instrumentId}`);

        if (!instrumentContainer) {
            // Create container if it doesn't exist
            instrumentContainer = document.createElement('div');
            instrumentContainer.id = `book-${instrumentId}`;
            instrumentContainer.className = 'instrument-container';
            marketDataDisplay.appendChild(instrumentContainer);
        }

        // Generate the HTML for the order book
        let html = `
            <h3>${instrumentId}</h3>
            <p>Last Update: ${new Date(data.timestamp * 1000).toLocaleTimeString()}</p>
            <div class="order-book-grid">
                <div class="asks-column">
                    <h4>Asks</h4>
                    <table>
                        <thead>
                            <tr><th>Price</th><th>Qty</th></tr>
                        </thead>
                        <tbody>
                            ${data.asks.reverse().map(level => `
                                <tr class="ask-row">
                                    <td class="price">${level.price.toFixed(2)}</td>
                                    <td class="quantity">${level.quantity}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
                <div class="spread">
                    <p class="best-bid">Bid: ${data.best_bid ? data.best_bid.price.toFixed(2) : 'N/A'}</p>
                    <p class="best-ask">Ask: ${data.best_ask ? data.best_ask.price.toFixed(2) : 'N/A'}</p>
                </div>
                <div class="bids-column">
                    <h4>Bids</h4>
                    <table>
                        <thead>
                            <tr><th>Price</th><th>Qty</th></tr>
                        </thead>
                        <tbody>
                            ${data.bids.map(level => `
                                <tr class="bid-row">
                                    <td class="price">${level.price.toFixed(2)}</td>
                                    <td class="quantity">${level.quantity}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
            <hr>
        `;
        instrumentContainer.innerHTML = html;
    }

    // Function to establish a WebSocket connection for a given instrument
    function connectWebSocket(instrumentId) {
        const ws = new WebSocket(`ws://localhost:8000/ws/market_data/${instrumentId}`);
        activeWebsockets[instrumentId] = ws;

        ws.onopen = (event) => {
            console.log(`WebSocket for ${instrumentId} connected!`);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // console.log(`Received data for ${instrumentId}:`, data); // For debugging
                updateOrderBookDisplay(data);
            } catch (e) {
                console.error(`Error parsing message for ${instrumentId}:`, e, event.data);
            }
        };

        ws.onclose = (event) => {
            console.log(`WebSocket for ${instrumentId} closed!`, event.code, event.reason);
            // Attempt to reconnect after a delay
            setTimeout(() => {
                console.log(`Reconnecting WebSocket for ${instrumentId}...`);
                connectWebSocket(instrumentId);
            }, 3000); // Reconnect after 3 seconds
        };

        ws.onerror = (event) => {
            console.error(`WebSocket error for ${instrumentId}:`, event);
        };
    }

    // Connect to WebSocket for each instrument
    instrumentsToSubscribe.forEach(instrumentId => {
        connectWebSocket(instrumentId);
    });

});