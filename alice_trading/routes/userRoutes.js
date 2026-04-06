import express from 'express';
import { getUserProfile, updateDisplayName, updateAccountPassword } from '../services/authService.js';

const router = express.Router();

// GET /user/profile → fetch profile data
router.get('/profile', async (req, res) => {
    try {
        const profile = await getUserProfile();
        res.status(200).json({ status: "success", data: profile });
    } catch (error) {
        res.status(401).json({ status: "error", message: error.message });
    }
});

// POST /user/update → update display name
router.post('/update', async (req, res) => {
    const { name } = req.body;
    try {
        const result = await updateDisplayName(name);
        res.status(200).json({ status: "success", data: result });
    } catch (error) {
        res.status(400).json({ status: "error", message: error.message });
    }
});

// POST /user/update-password → update password
router.post('/update-password', async (req, res) => {
    const { newPassword } = req.body;
    try {
        const result = await updateAccountPassword(newPassword);
        res.status(200).json({ status: "success", data: result });
    } catch (error) {
        res.status(400).json({ status: "error", message: error.message });
    }
});

export default router;
