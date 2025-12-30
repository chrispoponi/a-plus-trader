import axios from 'axios';

// PRODUCTION URL (Render)
const API_BASE_URL = 'https://a-plus-trader.onrender.com';

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
            const res = await axiosInstance.post(`/upload/${endpoint}`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
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
    liquidateAll: async () => {
        try {
            const res = await axiosInstance.post(`/api/emergency/liquidate`);
            return res.data;
        } catch (error) {
            console.error("Liquidation Failed", error);
            throw error;
        }
    }
};
