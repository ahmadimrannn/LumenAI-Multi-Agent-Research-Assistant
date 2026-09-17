/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useChatStore, Session } from '@/store/useChatStore';
import { authClient } from '@/lib/auth/client';
import { fetchUserSessions } from '@/lib/api';
import { Plus, MessageSquare, MoreVertical, Trash2, Edit2, LogIn, LogOut, Check, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface AppSidebarProps {
    user: any;
    authChecked: boolean;
    onOpenSignIn: () => void;
    onNewChat: () => void;
}

export function AppSidebar({ user, authChecked, onOpenSignIn, onNewChat }: AppSidebarProps) {
    const { sessions, activeSessionId, setActiveSession, deleteSession, renameSession } = useChatStore();
    const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
    const [editingTitle, setEditingTitle] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const lastUserIdRef = useRef<string | null>(null);

    useEffect(() => {
        if (!authChecked) return;

        if (!user?.id) {
            // Signed out: clear chat state locally. Never touch pendingQuery here —
            // the post-OAuth auto-resume depends on it surviving the redirect.
            useChatStore.setState({ sessions: [], activeSessionId: null, turnsBySession: {} });
            return;
        }

        let cancelled = false;
        const prevUserId = lastUserIdRef.current;
        lastUserIdRef.current = user.id;
        const switchedAccounts = Boolean(prevUserId && prevUserId !== user.id);

        async function loadRemoteSessions() {
            setIsLoading(true);
            try {
                const data = await fetchUserSessions();
                if (cancelled || !data?.sessions) return;

                const fetchedSessions: Session[] = data.sessions.map((s: any) => ({
                    id: s.thread_id,
                    title: s.title || 'Untitled Research',
                    createdAt: s.created_at || new Date().toISOString(),
                    updatedAt: s.updated_at || new Date().toISOString(),
                }));

                useChatStore.setState((state) => {
                    // Keep locally-created sessions that haven't been persisted server-side yet.
                    const localOnly = state.sessions.filter(
                        (s) => s.id.startsWith('temp_') && !fetchedSessions.some((r) => r.id === s.id)
                    );
                    const merged = [...localOnly, ...fetchedSessions];
                    const activeStillExists =
                        state.activeSessionId !== null &&
                        merged.some((s) => s.id === state.activeSessionId);
                    return {
                        sessions: merged,
                        turnsBySession: switchedAccounts ? {} : state.turnsBySession,
                        activeSessionId: activeStillExists ? state.activeSessionId : null,
                    };
                });
            } catch (err) {
                console.error('Failed to sync remote sessions:', err);
            } finally {
                if (!cancelled) setIsLoading(false);
            }
        }

        loadRemoteSessions();
        return () => {
            cancelled = true;
        };
    }, [authChecked, user?.id]);

    const groupedSessions = useMemo(() => {
        const now = new Date();
        const today: Session[] = [];
        const yesterday: Session[] = [];
        const previous7Days: Session[] = [];
        const older: Session[] = [];

        sessions.forEach((s) => {
            const date = new Date(s.updatedAt);
            const diffTime = Math.abs(now.getTime() - date.getTime());
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

            if (diffDays <= 1 && date.getDate() === now.getDate()) {
                today.push(s);
            } else if (diffDays <= 2) {
                yesterday.push(s);
            } else if (diffDays <= 7) {
                previous7Days.push(s);
            } else {
                older.push(s);
            }
        });

        return { Today: today, Yesterday: yesterday, 'Previous 7 days': previous7Days, Older: older };
    }, [sessions]);

    const handleSignOut = async () => {
        useChatStore.setState({
            sessions: [],
            activeSessionId: null
        });

        await authClient.signOut();
        window.location.reload();
    };

    const startRename = (s: Session) => {
        setEditingSessionId(s.id);
        setEditingTitle(s.title);
    };

    const saveRename = (id: string) => {
        if (editingTitle.trim()) {
            renameSession(id, editingTitle.trim());
        }
        setEditingSessionId(null);
    };

    const cancelRename = () => {
        setEditingSessionId(null);
    };

    const initials = user?.name
        ? user.name
            .split(' ')
            .map((n: string) => n[0])
            .join('')
            .slice(0, 2)
            .toUpperCase()
        : 'U';

    return (
        <aside className="flex h-full w-65 flex-col border-r border-neutral-200/80 bg-neutral-50 font-inter text-sm shrink-0 dark:border-neutral-800/80 dark:bg-neutral-950">
            {/* New Chat Header */}
            <div className="p-3 border-b border-neutral-200/60 dark:border-neutral-800/40">
                <Button
                    onClick={onNewChat}
                    variant="outline"
                    className="w-full justify-start border-neutral-300 bg-white font-inter text-xs text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900 dark:border-neutral-800 dark:bg-neutral-900/50 dark:text-neutral-200 dark:hover:bg-neutral-800 dark:hover:text-white"
                >
                    <Plus className="mr-2 h-4 w-4" />
                    New chat
                </Button>
            </div>

            {/* Recency Grouped Sessions List */}
            <div className="flex-1 min-h-0">
                <ScrollArea className="h-full px-3">
                    <div className="space-y-4 py-3">
                        {isLoading && (
                            <div className="flex items-center gap-2 px-2 text-xs text-neutral-500">
                                <Loader2 className="h-3 w-3 animate-spin" /> Loading sessions...
                            </div>
                        )}

                        {!isLoading && sessions.length === 0 ? (
                            <div className="px-2 text-xs text-neutral-500 italic">No recent chats</div>
                        ) : (
                            Object.entries(groupedSessions).map(([groupKey, groupItems]) => {
                                if (groupItems.length === 0) return null;
                                return (
                                    <div key={groupKey} className="space-y-1">
                                        <div className="px-2 text-[10px] font-medium tracking-wider text-neutral-500 uppercase">
                                            {groupKey}
                                        </div>
                                        {groupItems.map((s) => {
                                            const isActive = s.id === activeSessionId;
                                            const isEditing = s.id === editingSessionId;

                                            if (isEditing) {
                                                return (
                                                    <div key={s.id} className="flex items-center gap-1 px-1 py-1">
                                                        <Input
                                                            value={editingTitle}
                                                            onChange={(e) => setEditingTitle(e.target.value)}
                                                            onKeyDown={(e) => {
                                                                if (e.key === 'Enter') saveRename(s.id);
                                                                if (e.key === 'Escape') cancelRename();
                                                            }}
                                                            autoFocus
                                                            className="h-7 text-xs border-neutral-300 bg-white text-neutral-900 focus:ring-0 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
                                                        />
                                                        <Button
                                                            size="sm"
                                                            variant="ghost"
                                                            onClick={() => saveRename(s.id)}
                                                            className="h-7 w-7 p-0 text-emerald-600 hover:bg-neutral-100 dark:text-emerald-400 dark:hover:bg-neutral-800"
                                                            aria-label="Save new title"
                                                        >
                                                            <Check className="h-3.5 w-3.5" />
                                                        </Button>
                                                        <Button
                                                            size="sm"
                                                            variant="ghost"
                                                            onClick={cancelRename}
                                                            className="h-7 w-7 p-0 text-neutral-500 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800"
                                                            aria-label="Cancel rename"
                                                        >
                                                            <X className="h-3.5 w-3.5" />
                                                        </Button>
                                                    </div>
                                                );
                                            }

                                            return (
                                                <div
                                                    key={s.id}
                                                    onClick={() => setActiveSession(s.id)}
                                                    onDoubleClick={() => startRename(s)}
                                                    className={`group flex items-center justify-between rounded-lg px-2.5 py-2 cursor-pointer text-xs transition-colors ${isActive
                                                        ? 'bg-neutral-200/70 font-medium text-neutral-900 dark:bg-neutral-800/80 dark:text-neutral-100'
                                                        : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-900/80 dark:hover:text-neutral-200'
                                                        }`}
                                                >
                                                    <div className="flex items-center gap-2 truncate pr-1">
                                                        <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-60" />
                                                        <span className="truncate">{s.title}</span>
                                                    </div>

                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger
                                                            onClick={(e) => e.stopPropagation()}
                                                            className="inline-flex h-5 w-5 items-center justify-center rounded opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 hover:bg-neutral-200/60 dark:hover:bg-neutral-700/60"
                                                            aria-label="Session options"
                                                        >
                                                            <MoreVertical className="h-3 w-3 text-neutral-500 dark:text-neutral-400" />
                                                        </DropdownMenuTrigger>
                                                        <DropdownMenuContent align="end" className="border-neutral-200 bg-white text-neutral-700 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-200">
                                                            <DropdownMenuItem onClick={() => startRename(s)}>
                                                                <Edit2 className="mr-2 h-3.5 w-3.5" /> Rename
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem
                                                                onClick={() => deleteSession(s.id)}
                                                                className="text-red-600 focus:text-red-500 dark:text-red-400 dark:focus:text-red-300"
                                                            >
                                                                <Trash2 className="mr-2 h-3.5 w-3.5" /> Delete
                                                            </DropdownMenuItem>
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
                                                </div>
                                            );
                                        })}
                                    </div>
                                );
                            })
                        )}
                    </div>
                </ScrollArea>
            </div>

            {/* User Profile / Auth Section */}
            <div className="border-t border-neutral-200/80 p-3 dark:border-neutral-800/80">
                {user ? (
                    <div className="flex items-center justify-between gap-2 rounded-lg bg-neutral-100 p-2 dark:bg-neutral-900/40">
                        <div className="flex items-center gap-2.5 truncate">
                            <Avatar className="h-7 w-7 border border-neutral-300 dark:border-neutral-700">
                                <AvatarImage src={user.image} alt={user.name || 'User'} />
                                <AvatarFallback className="bg-neutral-200 text-[10px] font-medium text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300">
                                    {initials}
                                </AvatarFallback>
                            </Avatar>
                            <div className="flex flex-col truncate">
                                <span className="truncate text-xs font-medium text-neutral-800 dark:text-neutral-200">{user.name || 'User'}</span>
                                <span className="truncate text-[10px] text-neutral-500 dark:text-neutral-500">{user.email}</span>
                            </div>
                        </div>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleSignOut}
                            className="h-6 w-6 p-0 text-neutral-500 hover:text-neutral-900 dark:text-neutral-500 dark:hover:text-neutral-200"
                            aria-label="Sign out"
                        >
                            <LogOut className="h-3.5 w-3.5" />
                        </Button>
                    </div>
                ) : (
                    <Button
                        onClick={onOpenSignIn}
                        variant="ghost"
                        className="w-full justify-start font-inter text-xs text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-900 dark:hover:text-neutral-100"
                    >
                        <LogIn className="mr-2 h-4 w-4" />
                        Sign in
                    </Button>
                )}
            </div>
        </aside>
    );
}