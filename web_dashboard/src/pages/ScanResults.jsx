import React, { useState } from 'react';
import { api } from '../api';
import { Play, RefreshCw, Send, CheckCircle } from 'lucide-react';

const ScanPage = () => {
    const [results, setResults] = useState(null);
    const [scanning, setScanning] = useState(false);

    const handleScan = async () => {
        setScanning(true);
        try {
            const data = await api.runScan();
            setResults(data);
        } catch (e) {
            alert("Scan failed. Check backend console.");
        } finally {
            setScanning(false);
        }
    };

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold text-white">Market Scanner</h1>
                <button
                    onClick={handleScan}
                    disabled={scanning}
                    className="flex items-center gap-2 bg-pro-accent hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all px-6 py-2 rounded-lg font-semibold"
                >
                    {scanning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    {scanning ? 'Scanning...' : 'Run New Scan'}
                </button>
            </div>

            {!results && !scanning && (
                <div className="text-center py-20 text-gray-500 bg-pro-card rounded-xl border border-gray-800 border-dashed">
                    <p>No scan data loaded. Click "Run New Scan" to begin.</p>
                </div>
            )}

            {results && Object.entries(results).map(([section, candidates]) => (
                <div key={section} className="space-y-4">
                    <h2 className="text-xl font-bold text-gray-200 border-b border-gray-700 pb-2">{section}</h2>
                    {candidates.length === 0 ? (
                        <p className="text-gray-500 italic">No candidates found matching criteria ({'>'}= 65% Win Prob).</p>
                    ) : (
                        <div className="grid gap-4">
                            {candidates.map((c) => (
                                <div key={c.signal_id} className="bg-pro-card p-4 rounded-xl border border-gray-700 hover:border-pro-accent transition-colors group">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <div className="flex items-center gap-3">
                                                <span className="text-2xl font-bold text-white">{c.symbol}</span>
                                                <span className={`px-2 py-0.5 rounded text-xs font-bold ${c.direction === 'LONG' ? 'bg-pro-success/20 text-pro-success' : 'bg-pro-danger/20 text-pro-danger'}`}>
                                                    {c.direction}
                                                </span>
                                                <span className="text-sm text-gray-400">{c.setup_name}</span>
                                            </div>
                                            <p className="text-gray-300 mt-2 text-sm">{c.thesis}</p>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-3xl font-bold text-pro-success">{c.scores.win_probability_estimate.toFixed(1)}%</div>
                                            <div className="text-xs text-gray-500 uppercase tracking-widest">Win Prob</div>
                                        </div>
                                    </div>

                                    {/* Trade Plan Grid */}
                                    <div className="grid grid-cols-3 gap-4 mt-4 bg-pro-dark/50 p-3 rounded-lg border border-gray-800">
                                        <div>
                                            <div className="text-gray-500 text-xs uppercase">Entry</div>
                                            <div className="text-white font-mono font-medium">${c.trade_plan.entry}</div>
                                        </div>
                                        <div>
                                            <div className="text-gray-500 text-xs uppercase">Stop Loss</div>
                                            <div className="text-red-400 font-mono font-medium">${c.trade_plan.stop_loss}</div>
                                        </div>
                                        <div>
                                            <div className="text-gray-500 text-xs uppercase">Take Profit</div>
                                            <div className="text-green-400 font-mono font-medium">${c.trade_plan.take_profit}</div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};

export default ScanPage;
