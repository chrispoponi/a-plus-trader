import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { Play, Activity, TrendingUp, ShieldCheck } from 'lucide-react';

const Dashboard = () => {
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        checkHealth();
    }, []);

    const checkHealth = async () => {
        const data = await api.getHealth();
        setStatus(data);
        setLoading(false);
    };

    return (
        <div className="p-6 space-y-6">
            <h1 className="text-3xl font-bold text-white">Mission Control</h1>

            {/* Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-pro-card p-6 rounded-xl border border-gray-700 shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-400 text-sm font-medium">SYSTEM STATUS</h3>
                        <Activity className={`w-5 h-5 ${status?.status === 'system_active' ? 'text-pro-success' : 'text-pro-danger'}`} />
                    </div>
                    <p className="text-2xl font-bold capitalize">{status?.status?.replace('_', ' ') || 'Offline'}</p>
                </div>

                <div className="bg-pro-card p-6 rounded-xl border border-gray-700 shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-400 text-sm font-medium">ACTIVE MODE</h3>
                        <ShieldCheck className="w-5 h-5 text-pro-warning" />
                    </div>
                    <p className="text-2xl font-bold tracking-wider">{status?.mode || '---'}</p>
                </div>

                <div className="bg-pro-card p-6 rounded-xl border border-gray-700 shadow-lg">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-400 text-sm font-medium">RISK LIMIT</h3>
                        <TrendingUp className="w-5 h-5 text-pro-accent" />
                    </div>
                    <p className="text-2xl font-bold">{status ? `${(status.risk_limit * 100).toFixed(1)}% / Trade` : '---'}</p>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="mt-8">
                <h2 className="text-xl font-bold mb-4">Quick Actions</h2>
                <div className="flex gap-4">
                    <button className="flex items-center gap-2 bg-pro-accent hover:bg-blue-600 transition-colors px-6 py-3 rounded-lg font-semibold shadow-lg shadow-blue-900/20">
                        <Play className="w-4 h-4" />
                        Run Full Scan
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
