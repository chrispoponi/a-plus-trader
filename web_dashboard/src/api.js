import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const api = {
    getHealth: async () => {
        try {
            const res = await axios.get(`${API_BASE_URL}/`);
            return res.data;
        } catch (error) {
            console.error("Health Check Failed", error);
            return { status: "offline" };
        }
    },
    runScan: async () => {
        try {
            const res = await axios.get(`${API_BASE_URL}/scan`);
            return res.data;
        } catch (error) {
            console.error("Scan Failed", error);
            throw error;
        }
    },
    getUploads: async () => {
        try {
            const res = await axios.get(`${API_BASE_URL}/upload/list`);
            return res.data;
        } catch (error) {
            console.error("Fetch Uploads Failed", error);
            return {};
        }
    }
};
