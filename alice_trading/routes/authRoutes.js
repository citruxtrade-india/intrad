import express from 'express';
import { signupUser, loginUser, forgotPasswordAccount } from '../services/authService.js';

const router = express.Router();

// POST /auth/signup -> creates user and sends verification email
router.post('/signup', async (req, res) => {
    const { email, password } = req.body;
    
    if (!email || !password) {
        return res.status(400).json({ status: "error", message: "Email and password are required." });
    }
    
    try {
        const result = await signupUser(email, password);
        res.status(201).json({ status: "success", data: result });
    } catch (error) {
        res.status(400).json({ status: "error", message: error.message });
    }
});

// POST /auth/login -> logs in user and checks if email is verified
router.post('/login', async (req, res) => {
    const { email, password } = req.body;
    
    if (!email || !password) {
        return res.status(400).json({ status: "error", message: "Email and password are required." });
    }
    
    try {
        const result = await loginUser(email, password);
        res.status(200).json({ status: "success", data: result });
    } catch (error) {
        const statusCode = error.message.includes("Email not verified") ? 403 : 401;
        res.status(statusCode).json({ status: "error", message: error.message });
    }
});

// POST /auth/forgot-password -> sends recovery link via Firebase
router.post('/forgot-password', async (req, res) => {
    const { email } = req.body;
    if (!email) {
        return res.status(400).json({ status: "error", message: "Institutional email required." });
    }
    try {
        const result = await forgotPasswordAccount(email);
        res.status(200).json({ status: "success", message: result.message });
    } catch (error) {
        res.status(500).json({ status: "error", message: error.message });
    }
});

export default router;
