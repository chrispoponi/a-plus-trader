import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { Server, Database, Activity, FileText, Smartphone } from 'lucide-react';

const ControlCenter = () => {
    const [uploads, setUploads] = useState({});
    const [health, setHealth] = useState({ status: 'checking' });

    useEffect(() => {
        const fetchData = async () => {
            const h = await api.getHealth();
            setHealth(h);
            const files = await api.getUploads();
            setUploads(files);
        };
        fetchData();
        const interval = setInterval(fetchData, 10000); // Refresh every 10s
        return () => clearInterval(interval);
    }, []);

    const StatusBadge = ({ label, value, active }) => (
        <div className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700">
            <span className="text-gray-400 text-sm">{label}</span>
            <span className={`text-sm font-bold ${active ? 'text-pro-success' : 'text-gray-500'}`}>
                {value}
            </span>
        </div>
    );

    return (
        <div className="p-6 space-y-6">
            <header>
                <h1 className="text-3xl font-bold text-white">Command Center</h1>
                <p className="text-gray-400">System Visibility & Controls</p>
            </header>

            {/* TOP ROW: HEALTH & DATA */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* COLUMN 1: SYSTEM HEALTH */}
                <div className="space-y-6">
                    <div className="bg-pro-card p-5 rounded-xl border border-gray-700 h-full">
                        <div className="flex items-center gap-2 mb-4 text-white font-semibold">
                            <Server className="w-5 h-5 text-pro-accent" />
                            <h3>Core System</h3>
                        </div>
                        <div className="space-y-3">
                            <StatusBadge
                                label="Engine Status"
                                value={health.status === 'system_active' ? 'ONLINE' : 'OFFLINE'}
                                active={health.status === 'system_active'}
                            />
                            <StatusBadge
                                label="Trading Mode"
                                value={health.mode || 'N/A'}
                                active={health.mode === 'LIVE' || health.mode === 'PAPER'}
                            />
                            <StatusBadge
                                label="Risk Limit"
                                value={`${health.risk_limit ? (health.risk_limit * 100).toFixed(2) : '-'}%`}
                                active={true}
                            />
                        </div>
                    </div>
                </div>

                {/* COLUMN 2 & 3: DATA INVENTORY */}
                <div className="bg-pro-card p-5 rounded-xl border border-gray-700 lg:col-span-2">
                    <div className="flex items-center gap-2 mb-6 text-white font-semibold">
                        <Database className="w-5 h-5 text-pro-warning" />
                        <h3>Data Inventory</h3>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {['chatgpt', 'tradingview', 'finviz'].map((source) => (
                            <div key={source} className="bg-gray-800/50 p-4 rounded-lg border border-gray-700">
                                <h4 className="text-sm font-bold text-gray-300 uppercase mb-3 flex items-center justify-between">
                                    {source}
                                    <span className="text-xs bg-gray-700 px-2 py-0.5 rounded text-white">{uploads[source]?.length || 0}</span>
                                </h4>
                                <div className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
                                    {uploads[source] && uploads[source].length > 0 ? (
                                        uploads[source].map((file, i) => (
                                            <div key={i} className="flex items-center gap-2 text-xs text-gray-400">
                                                <FileText className="w-3 h-3 flex-shrink-0" />
                                                <span className="truncate">{file}</span>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-xs text-gray-600 italic">No files uploaded</div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="mt-6 bg-gray-800/50 p-4 rounded-lg border border-gray-700">
                        <h4 className="text-sm font-bold text-gray-300 uppercase mb-3 flex items-center justify-between">
                            ChatGPT Automation Drops
                            <span className="text-xs bg-gray-700 px-2 py-0.5 rounded text-white">{uploads['chatgpt_automation']?.length || 0}</span>
                        </h4>
                        <div className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
                            {uploads['chatgpt_automation'] && uploads['chatgpt_automation'].length > 0 ? (
                                uploads['chatgpt_automation'].map((file, i) => (
                                    <div key={i} className="flex items-center gap-2 text-xs text-gray-400">
                                        <Activity className="w-3 h-3 text-green-500 flex-shrink-0" />
                                        <span className="truncate">{file}</span>
                                    </div>
                                ))
                            ) : (
                                <div className="text-xs text-gray-600 italic">No automation drops received yet</div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* BOTTOM ROW: BOT INTERFACE (FULL WIDTH) */}
            <div className="bg-pro-card p-5 rounded-xl border border-gray-700">
                <div className="flex items-center gap-2 mb-4 text-white font-semibold">
                    <Smartphone className="w-5 h-5 text-purple-400" />
                    <h3>Bot Interface (Backend API)</h3>
                </div>
                <div className="w-full bg-white rounded-lg overflow-hidden relative" style={{ height: '600px' }}>
                    <iframe
                        src="http://localhost:8000/docs"
                        className="w-full h-full border-0"
                        title="Backend Docs"
                    />
                </div>
            </div>
        </div>
    );
};

export default ControlCenter;
