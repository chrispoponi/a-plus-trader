import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Target, Zap, Layers, Settings, Terminal, Database, BarChart2 } from 'lucide-react';

const Layout = ({ children }) => {
    const menuItems = [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
        { icon: BarChart2, label: 'Live Charts', path: '/charts' },
        { icon: Zap, label: 'Run Scan', path: '/scan' },
        { type: 'divider', label: 'Strategies' },
        { icon: Target, label: 'Swing Setups', path: '/swing' },
        { icon: Terminal, label: 'Breakouts', path: '/breakouts' },
        { icon: Layers, label: 'Options', path: '/options' },
        { type: 'divider', label: 'Data Source' },
        { icon: Database, label: 'Data Ingest', path: '/ingest' },
        { type: 'divider', label: 'System' },
        { icon: Settings, label: 'Settings', path: '/settings' },
    ];

    return (
        <div className="flex min-h-screen bg-pro-dark text-white">
            {/* Sidebar */}
            <div className="w-64 border-r border-gray-800 bg-pro-card flex-shrink-0">
                <div className="p-6 border-b border-gray-800">
                    <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                        A+ TRADER
                    </h1>
                    <p className="text-xs text-gray-500 mt-1">AI-Powered Signal Engine</p>
                </div>

                <nav className="p-4 space-y-1">
                    {menuItems.map((item, idx) => (
                        item.type === 'divider' ? (
                            <div key={idx} className="pt-4 pb-2 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                {item.label}
                            </div>
                        ) : (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={({ isActive }) =>
                                    `flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${isActive
                                        ? 'bg-pro-accent/10 text-pro-accent'
                                        : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                                    }`
                                }
                            >
                                <item.icon className="w-5 h-5" />
                                <span className="font-medium">{item.label}</span>
                            </NavLink>
                        )
                    ))}
                </nav>
            </div>

            {/* Main Content */}
            <main className="flex-1 overflow-auto bg-pro-dark">
                {children}
            </main>
        </div>
    );
};

export default Layout;
