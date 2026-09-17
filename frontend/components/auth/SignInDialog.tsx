'use client';

import { authClient } from '@/lib/auth/client';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface SignInDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

function GoogleIcon() {
    return (
        <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
            <path
                fill="#4285F4"
                d="M23.52 12.273c0-.851-.076-1.67-.218-2.455H12v4.642h6.458a5.52 5.52 0 0 1-2.394 3.622v3.012h3.878c2.27-2.087 3.578-5.165 3.578-8.821z"
            />
            <path
                fill="#34A853"
                d="M12 24c3.24 0 5.956-1.075 7.942-2.908l-3.878-3.012c-1.075.72-2.45 1.146-4.064 1.146-3.126 0-5.77-2.11-6.71-4.947H1.276v3.109A11.995 11.995 0 0 0 12 24z"
            />
            <path
                fill="#FBBC05"
                d="M5.29 14.28A7.213 7.213 0 0 1 4.914 12c0-.794.137-1.564.376-2.28V6.611H1.276a11.995 11.995 0 0 0 0 10.778L5.29 14.28z"
            />
            <path
                fill="#EA4335"
                d="M12 4.773c1.762 0 3.344.605 4.587 1.794l3.442-3.442C17.951 1.19 15.235 0 12 0A11.995 11.995 0 0 0 1.276 6.61L5.29 9.72C6.23 6.884 8.874 4.773 12 4.773z"
            />
        </svg>
    );
}

export function SignInDialog({ open, onOpenChange }: SignInDialogProps) {
    const handleGoogleSignIn = async () => {
        await authClient.signIn.social({
            provider: 'google',
            callbackURL: window.location.origin,
        });
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="border-neutral-200 bg-white font-inter text-neutral-900 sm:max-w-95 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-100">
                <DialogHeader className="space-y-1.5">
                    <DialogTitle className="font-geist text-lg tracking-tighter font-medium text-neutral-900 dark:text-neutral-100">
                        Sign in to Lumen
                    </DialogTitle>
                    <DialogDescription className="font-inter text-xs text-neutral-500 dark:text-neutral-400">
                        Authentication is required to query the research agent pipeline.
                    </DialogDescription>
                </DialogHeader>

                <div className="py-3">
                    <Button
                        onClick={handleGoogleSignIn}
                        className="w-full bg-neutral-900 font-inter text-xs font-medium text-white hover:bg-neutral-700 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-200"
                    >
                        <GoogleIcon />
                        Continue with Google
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
