import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { Play, Activity, TrendingUp, ShieldCheck, X } from 'lucide-react';
import PerformanceChart from '../components/PerformanceChart';

const ControlCenter = () => {
    const [status, setStatus] = useState(null);
    const [stats, setStats] = useState(null);
    const [history, setHistory] = useState([]);
    const [positions, setPositions] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        const health = await api.getHealth();
        const jStats = await api.getJournalStats();
        const jHist = await api.getJournalHistory();
        const pos = await api.getPositions();

        setStatus(health);
        setStats(jStats);
        setHistory(jHist);
        setPositions(pos);
        setLoading(false);
    };

    return (
        <div className="p-6 space-y-8">
            <h1 className="text-3xl font-bold text-white">MISSION CONTROL - LIVE VERIFIED</h1>

            {/* Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-pro-card p-6 rounded-xl border border-gray-700 shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-400 text-sm font-medium">SYSTEM STATUS</h3>
                        <Activity className={`w-5 h-5 ${status?.status === 'system_active' ? 'text-pro-success' : 'text-pro-danger'}`} />
                    </div>
                    <p className="text-2xl font-bold capitalize">{status?.status?.replace('_', ' ') || 'Offline'}</p>
                </div>

                <div className="bg-pro-card p-6 rounded-xl border border-gray-700 shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-400 text-sm font-medium">MODE</h3>
                        <ShieldCheck className="w-5 h-5 text-pro-warning" />
                    </div>
                    <p className="text-2xl font-bold tracking-wider">{status?.mode || '---'}</p>
                </div>

                <div className="bg-pro-card p-6 rounded-xl border border-gray-700 shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-400 text-sm font-medium">WIN RATE</h3>
                        <TrendingUp className="w-5 h-5 text-pro-accent" />
                    </div>
                    <p className="text-2xl font-bold text-white">
                        {stats?.win_rate ? (stats.win_rate * 100).toFixed(1) + '%' : 'N/A'}
                    </p>
                </div>

                <div className="bg-pro-card p-6 rounded-xl border border-gray-700 shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-400 text-sm font-medium">NET PnL</h3>
                        <span className="text-xs text-gray-500">REALIZED</span>
                    </div>
                    <p className={`text-2xl font-bold ${stats?.total_pnl >= 0 ? 'text-pro-success' : 'text-pro-danger'}`}>
                        {stats?.total_pnl ? `$${stats.total_pnl.toFixed(2)}` : '$0.00'}
                    </p>
                </div>
            </div>

            {/* Equity Curve Chart */}
            <PerformanceChart trades={history} />

            {/* LIVE PORTFOLIO */}
            <div className="bg-pro-card rounded-xl border border-gray-700 overflow-hidden">
                <div className="p-4 border-b border-gray-700 flex justify-between items-center">
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-blue-400" />
                        Active Portfolio (Live)
                    </h2>
                    <span className="text-sm text-gray-400">{positions.length} Open Positions</span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-gray-800/50 text-gray-400 uppercase text-xs">
                            <tr>
                                <th className="px-6 py-3">Symbol</th>
                                <th className="px-6 py-3">Qty</th>
                                <th className="px-6 py-3">Mkt Value</th>
                                <th className="px-6 py-3 text-right">Cost Basis</th>
                                <th className="px-6 py-3 text-right">Unrealized P&L</th>
                                <th className="px-6 py-3 text-right">% Return</th>
                                <th className="px-6 py-3 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700">
                            {positions.length > 0 ? (
                                positions.map((p) => (
                                    <tr key={p.symbol} className="hover:bg-gray-700/30 transition-colors">
                                        <td className="px-6 py-4 font-bold text-white">{p.symbol}</td>
                                        <td className={`px-6 py-4 font-mono ${p.qty < 0 ? 'text-purple-400' : 'text-blue-400'}`}>
                                            {p.qty}
                                        </td>
                                        <td className="px-6 py-4 font-mono">${p.market_value?.toFixed(2)}</td>
                                        <td className="px-6 py-4 font-mono text-right text-gray-400">${p.cost_basis?.toFixed(2)}</td>
                                        <td className={`px-6 py-4 font-bold text-right ${p.unrealized_pl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            ${p.unrealized_pl?.toFixed(2)}
                                        </td>
                                        <td className={`px-6 py-4 font-bold text-right ${p.unrealized_plpc >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            {(p.unrealized_plpc * 100).toFixed(2)}%
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button
                                                onClick={async () => {
                                                    if (confirm(`Market Sell ${p.symbol}?`)) {
                                                        await api.closePosition(p.symbol);
                                                        // Optimistic Update
                                                        setPositions(prev => prev.filter(pos => pos.symbol !== p.symbol));
                                                    }
                                                }}
                                                className="bg-red-900/40 hover:bg-red-600 text-red-400 hover:text-white p-2 rounded-full transition-colors"
                                                title="Close Position"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan="6" className="px-6 py-8 text-center text-gray-500 italic">No active positions found.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Performance Log */}
            <div className="bg-pro-card rounded-xl border border-gray-700 overflow-hidden">
                <div className="p-4 border-b border-gray-700 flex justify-between items-center">
                    <h2 className="text-lg font-bold text-white">Recent Trade Log</h2>
                    <span className="text-sm text-gray-400">{history.length} Entries</span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-gray-800/50 text-gray-400 uppercase text-xs">
                            <tr>
                                <th className="px-6 py-3">Time</th>
                                <th className="px-6 py-3">Symbol</th>
                                <th className="px-6 py-3">Type</th>
                                <th className="px-6 py-3">Entry</th>
                                <th className="px-6 py-3">Exit</th>
                                <th className="px-6 py-3 text-right">PnL</th>
                                <th className="px-6 py-3 text-right">R-Mult</th>
                                <th className="px-6 py-3 text-center">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700">
                            {history.length > 0 ? (
                                history.slice().reverse().map((t) => (
                                    <tr key={t.trade_id} className="hover:bg-gray-700/30 transition-colors">
                                        <td className="px-6 py-4 font-mono text-gray-400">{new Date(t.entry_time).toLocaleTimeString()}</td>
                                        <td className="px-6 py-4 font-bold text-white">{t.symbol}</td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded text-xs font-bold ${t.bucket === 'DAY_TRADE' ? 'bg-blue-500/20 text-blue-400' : 'bg-purple-500/20 text-purple-400'}`}>
                                                {t.bucket}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 font-mono">${t.entry_price?.toFixed(2)}</td>
                                        <td className="px-6 py-4 font-mono">{t.exit_price ? `$${t.exit_price.toFixed(2)}` : '-'}</td>
                                        <td className={`px-6 py-4 text-right font-bold ${t.pnl_dollars > 0 ? 'text-green-400' : t.pnl_dollars < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                                            {t.pnl_dollars ? `$${t.pnl_dollars.toFixed(2)}` : '-'}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono">{t.r_multiple ? `${t.r_multiple.toFixed(2)}R` : '-'}</td>
                                        <td className="px-6 py-4 text-center">
                                            <span className={`px-2 py-1 rounded text-xs ${t.status === 'CLOSED' ? 'bg-gray-700 text-gray-300' : 'bg-green-500/20 text-green-400 animate-pulse'}`}>
                                                {t.status}
                                            </span>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan="8" className="px-6 py-8 text-center text-gray-500 italic">No trades recorded locally.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="flex gap-4 items-center">
                <a href="/scan" className="flex items-center gap-2 bg-pro-accent hover:bg-blue-600 transition-colors px-6 py-3 rounded-lg font-semibold shadow-lg shadow-blue-900/20 text-white">
                    <Play className="w-4 h-4" />
                    Launch Scanner
                </a>

                <button
                    onClick={async () => {
                        if (confirm("Clear all data files?")) {
                            await api.clearData();
                            location.reload();
                        }
                    }}
                    className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 transition-colors px-6 py-3 rounded-lg font-bold shadow-lg text-white border border-gray-600"
                >
                    CLEAR DATA
                </button>

                <button
                    onClick={async () => {
                        if (confirm("⚠️ CRITICAL WARNING ⚠️\n\nThis will immediately MARKET SELL all open positions and CANCEL all orders.\n\nAre you sure you want to go to 100% CASH?")) {
                            try {
                                await api.liquidateAll();
                                alert("Liquidation Sequence Initiated.");
                            } catch (e) {
                                alert("LIQUIDATION FAILED: " + e.message);
                            }
                        }
                    }}
                    className="flex items-center gap-2 bg-red-600 hover:bg-red-700 transition-colors px-6 py-3 rounded-lg font-bold shadow-lg shadow-red-900/20 text-white border border-red-500"
                >
                    <div className="w-3 h-3 bg-white rounded-full animate-pulse mr-1" />
                    LIQUIDATE ALL POSITIONS
                </button>
            </div>
        </div>
    );
};

export default ControlCenter;
