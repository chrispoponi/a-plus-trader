import React, { useState } from 'react';
import TradingViewWidget from '../components/TradingViewWidget';
import { Search } from 'lucide-react';

const ChartPage = () => {
    const [symbol, setSymbol] = useState("NASDAQ:NVDA");
    const [input, setInput] = useState("NASDAQ:NVDA");

    const handleSearch = (e) => {
        e.preventDefault();
        setSymbol(input.toUpperCase());
    };

    return (
        <div className="flex flex-col h-full p-6 space-y-4">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">Live Charts</h1>
                    <p className="text-gray-400 mt-1">Real-time market analysis provided by TradingView.</p>
                </div>

                <form onSubmit={handleSearch} className="flex items-center gap-2 bg-gray-800 p-2 rounded-lg border border-gray-700">
                    <Search className="w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        className="bg-transparent border-none outline-none text-white w-40 placeholder-gray-500 uppercase font-medium"
                        placeholder="SYMBOL"
                    />
                    <button type="submit" className="bg-pro-accent hover:bg-blue-600 text-white px-4 py-1 rounded text-sm font-bold transition-colors">
                        LOAD
                    </button>
                </form>
            </div>

            <div className="flex-1 min-h-[600px]">
                <TradingViewWidget key={symbol} symbol={symbol} />
            </div>
        </div>
    );
};

export default ChartPage;
