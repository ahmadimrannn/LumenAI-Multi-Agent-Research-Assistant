'use client';

import { useTheme } from 'next-themes';
import { Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function ThemeToggle() {
    const { resolvedTheme, setTheme } = useTheme();

    return (
        <Button
            variant="ghost"
            size="sm"
            onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
            className="h-8 w-8 p-0 text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-200"
            aria-label="Toggle color theme"
        >
            <Sun className="h-4 w-4 dark:hidden" />
            <Moon className="hidden h-4 w-4 dark:block" />
        </Button>
    );
}
