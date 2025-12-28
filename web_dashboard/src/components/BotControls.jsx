import React, { useState } from 'react';
import { api } from '../api';
import { Play, UploadCloud, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';

const BotControls = ({ onRefresh }) => {
    const [loading, setLoading] = useState(false);
    const [statusMsg, setStatusMsg] = useState(null);

    const handleRunScan = async () => {
        setLoading(true);
        setStatusMsg({ type: 'info', text: 'Initializing Market Scan...' });
        try {
            const results = await api.runScan();
            console.log(results);
            setStatusMsg({ type: 'success', text: 'Scan Complete! Check "Scan Results" page.' });
        } catch (err) {
            setStatusMsg({ type: 'error', text: 'Scan Failed. Check Backend Logs.' });
        }
        setLoading(false);
    };

    const handleUpload = async (source, event) => {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        setLoading(true);
        setStatusMsg({ type: 'info', text: `Uploading to ${source}...` });

        try {
            await api.uploadFile(source, formData);
            setStatusMsg({ type: 'success', text: `${source.toUpperCase()} Upload Successful!` });
            if (onRefresh) onRefresh();
        } catch (err) {
            setStatusMsg({ type: 'error', text: `Upload Failed: ${err.message}` });
        }
        setLoading(false);
    };

    return (
        <div className="flex flex-col h-full">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h3 className="text-xl font-bold text-white">Manual Operations</h3>
                    <p className="text-sm text-gray-400">Direct Control Override</p>
                </div>
                {statusMsg && (
                    <div className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 ${statusMsg.type === 'success' ? 'bg-green-900/30 text-green-400 border border-green-800' :
                            statusMsg.type === 'error' ? 'bg-red-900/30 text-red-400 border border-red-800' :
                                'bg-blue-900/30 text-blue-400 border border-blue-800'
                        }`}>
                        {statusMsg.type === 'success' ? <CheckCircle className="w-4 h-4" /> :
                            statusMsg.type === 'error' ? <AlertCircle className="w-4 h-4" /> :
                                <RefreshCw className="w-4 h-4 animate-spin" />}
                        {statusMsg.text}
                    </div>
                )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* CARD 1: SCAN TRIGGER */}
                <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 flex flex-col items-center justify-center text-center hover:border-gray-600 transition-colors">
                    <div className="bg-pro-accent/10 p-4 rounded-full mb-4">
                        <Play className="w-8 h-8 text-pro-accent" />
                    </div>
                    <h4 className="text-white font-bold text-lg mb-2">Execute Market Scan</h4>
                    <p className="text-gray-400 text-sm mb-6 max-w-xs">
                        Force the bot to run a full analysis cycle immediately using current data.
                    </p>
                    <button
                        onClick={handleRunScan}
                        disabled={loading}
                        className="bg-pro-accent hover:bg-pro-accent/90 text-white font-bold py-3 px-8 rounded-lg shadow-lg hover:shadow-pro-accent/20 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? 'Processing...' : 'RUN SCAN NOW'}
                    </button>
                </div>

                {/* CARD 2: DATA UPLOAD */}
                <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
                    <h4 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
                        <UploadCloud className="w-5 h-5 text-pro-warning" />
                        Manual Data Ingest
                    </h4>
                    <div className="space-y-4">
                        {['chatgpt', 'tradingview', 'finviz'].map((source) => (
                            <div key={source} className="group relative">
                                <label className="flex items-center justify-between p-4 bg-gray-900/50 border border-gray-700 rounded-lg cursor-pointer hover:bg-gray-800 hover:border-gray-500 transition-all">
                                    <div className="flex items-center gap-3">
                                        <div className="w-2 h-2 rounded-full bg-gray-600 group-hover:bg-pro-warning transition-colors" />
                                        <span className="text-gray-300 font-medium capitalize">{source} CSV</span>
                                    </div>
                                    <span className="text-xs text-gray-500 uppercase font-bold tracking-wider group-hover:text-white transition-colors">Select File</span>
                                    <input
                                        type="file"
                                        accept=".csv"
                                        className="hidden"
                                        onChange={(e) => handleUpload(source, e)}
                                        disabled={loading}
                                    />
                                </label>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default BotControls;
