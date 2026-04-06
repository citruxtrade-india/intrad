import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import authRoutes from './routes/authRoutes.js';
import userRoutes from './routes/userRoutes.js';

dotenv.config();

const app = express();

app.use(cors());
app.use(express.json());

// Load auth routes
app.use('/auth', authRoutes);
app.use('/user', userRoutes);

const PORT = process.env.NODE_PORT || 3000;

app.listen(PORT, () => {
    console.log(`Node.js Firebase Auth API running on port ${PORT}`);
});
