import React from 'react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer
} from 'recharts';

const PerformanceChart = ({ trades }) => {
    // 1. Process Data
    // Filter closed trades and sort by time form oldest to newest
    const data = trades
        .filter(t => t.status === 'CLOSED' || t.pnl_dollars !== 0)
        .sort((a, b) => new Date(a.entry_time) - new Date(b.entry_time))
        .reduce((acc, t) => {
            const prevEquity = acc.length > 0 ? acc[acc.length - 1].equity : 0;
            acc.push({
                time: new Date(t.entry_time).toLocaleDateString(),
                pnl: t.pnl_dollars,
                equity: prevEquity + (t.pnl_dollars || 0)
            });
            return acc;
        }, []);

    if (data.length === 0) {
        return (
            <div className="h-64 flex items-center justify-center text-gray-500 bg-pro-card rounded-xl border border-gray-700">
                No Closed Trades to Chart
            </div>
        );
    }

    return (
        <div className="bg-pro-card p-4 rounded-xl border border-gray-700 shadow-lg">
            <h3 className="text-gray-400 text-sm font-medium mb-4">EQUITY CURVE</h3>
            <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data}>
                        <defs>
                            <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis
                            dataKey="time"
                            stroke="#9ca3af"
                            fontSize={12}
                            tickFormatter={(val) => val.split('/')[0] + '/' + val.split('/')[1]}
                        />
                        <YAxis
                            stroke="#9ca3af"
                            fontSize={12}
                            tickFormatter={(val) => `$${val}`}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#f3f4f6' }}
                            itemStyle={{ color: '#60a5fa' }}
                            formatter={(val) => [`$${val.toFixed(2)}`, 'Net Equity']}
                        />
                        <Area
                            type="monotone"
                            dataKey="equity"
                            stroke="#3b82f6"
                            fillOpacity={1}
                            fill="url(#colorEquity)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default PerformanceChart;
