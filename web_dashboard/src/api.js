import axios from 'axios';

// PRODUCTION URL (Render) vs LOCAL
const API_BASE_URL = import.meta.env.PROD
    ? 'https://a-plus-trader.onrender.com'
    : 'http://localhost:8000';

const axiosInstance = axios.create({
    baseURL: API_BASE_URL,
    timeout: 60000, // 60 seconds
});

export const api = {
    getHealth: async () => {
        try {
            const res = await axiosInstance.get(`/`);
            return res.data;
        } catch (error) {
            console.error("Health Check Failed", error);
            return { status: "offline" };
        }
    },
    runScan: async () => {
        try {
            const res = await axiosInstance.get(`/scan`);
            return res.data;
        } catch (error) {
            console.error("Scan Failed", error);
            throw error;
        }
    },
    getUploads: async () => {
        try {
            const res = await axiosInstance.get(`/upload/list`);
            return res.data;
        } catch (error) {
            console.error("Fetch Uploads Failed", error);
            return {};
        }
    },
    uploadFile: async (endpoint, formData) => {
        try {
            const res = await axiosInstance.post(`/upload/${endpoint}`, formData);
            return res.data;
        } catch (error) {
            console.error(`Upload to ${endpoint} Failed`, error);
            throw error;
        }
    },
    getJournalStats: async () => {
        try {
            const res = await axiosInstance.get(`/api/journal/stats`);
            return res.data;
        } catch (error) {
            return {};
        }
    },
    getJournalHistory: async () => {
        try {
            const res = await axiosInstance.get(`/api/journal/history`);
            return res.data;
        } catch (error) {
            return [];
        }
    },
    clearData: async () => {
        try {
            const res = await axiosInstance.post(`/api/data/clear`);
            return res.data;
        } catch (error) {
            console.error("Clear Data Failed", error);
            throw error;
        }
    },
    getPositions: async () => {
        try {
            const res = await axiosInstance.get(`/api/alpaca/positions`);
            return res.data;
        } catch (error) {
            console.error("Fetch Positions Failed", error);
            return [];
        }
    },
    liquidateAll: async () => {
        try {
            const res = await axiosInstance.post(`/api/emergency/liquidate`);
            return res.data;
        } catch (error) {
            console.error("Liquidation Failed", error);
            throw error;
        }
    },
    closePosition: async (symbol) => {
        try {
            const res = await axiosInstance.post(`/api/alpaca/close_position`, { symbol });
            return res.data;
        } catch (error) {
            console.error("Close Position Failed", error);
            throw error;
        }
    }
};
