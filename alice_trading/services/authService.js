import { auth } from './firebase.js';
import { 
    createUserWithEmailAndPassword, 
    signInWithEmailAndPassword, 
    sendEmailVerification,
    updateProfile,
    updatePassword,
    sendPasswordResetEmail
} from "firebase/auth";

export const signupUser = async (email, password) => {
    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        
        // Send email verification explicitly via Firebase rules
        await sendEmailVerification(user);
        
        return {
            uid: user.uid,
            email: user.email,
            emailVerified: user.emailVerified,
            message: "User created successfully. Verification email sent."
        };
    } catch (error) {
        throw new Error(error.message);
    }
};

export const loginUser = async (email, password) => {
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        
        // Block login strictly if email is not verified (Firebase client rule)
        if (!user.emailVerified) {
            throw new Error("Email not verified. Please check your inbox and verify your email address before attempting to login.");
        }
        
        return {
            uid: user.uid,
            email: user.email,
            emailVerified: user.emailVerified,
            accessToken: await user.getIdToken()
        };
    } catch (error) {
        throw new Error(error.message);
    }
};
export const getUserProfile = async () => {
    const user = auth.currentUser;
    if (!user) throw new Error("Authentication required.");
    return {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName || "Institutional Trader",
        emailVerified: user.emailVerified,
        creationTime: user.metadata.creationTime,
        lastSignInTime: user.metadata.lastSignInTime
    };
};

export const updateDisplayName = async (name) => {
    const user = auth.currentUser;
    if (!user) throw new Error("Authentication required.");
    try {
        await updateProfile(user, { displayName: name });
        return { message: "Display name updated successfully." };
    } catch (error) {
        throw new Error(error.message);
    }
};

export const updateAccountPassword = async (newPassword) => {
    const user = auth.currentUser;
    if (!user) throw new Error("Authentication required.");
    try {
        await updatePassword(user, newPassword);
        return { message: "Password updated successfully." };
    } catch (error) {
        throw new Error(error.message);
    }
};

export const forgotPasswordAccount = async (email) => {
    try {
        await sendPasswordResetEmail(auth, email);
        return { message: "Security Protocol: Recovery link transmitted to registered endpoint." };
    } catch (error) {
        throw new Error(error.message);
    }
};
