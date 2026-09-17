/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import { useState, useEffect, useRef } from 'react';
import { useChatStore } from '@/store/useChatStore';
import { authClient } from '@/lib/auth/client';
import { streamResearch, fetchThreadHistory } from '@/lib/api/research';
import { AppSidebar } from '@/components/sidebar/AppSidebar';
import { TurnView } from '@/components/chat/TurnView';
import { SignInDialog } from '@/components/auth/SignInDialog';
import { ThemeToggle } from '@/components/theme-toggle';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
    ArrowUp,
    Menu,
    PanelLeftClose,
    PanelLeft,
    Loader2,
    MoreHorizontal,
    Pencil,
    Trash2,
    Check,
    X,
} from 'lucide-react';

export default function ChatPage() {
    const [currentUser, setCurrentUser] = useState<any>(null);
    const [authChecked, setAuthChecked] = useState(false);
    const [isSignInOpen, setIsSignInOpen] = useState(false);
    const [isLoadingHistory, setIsLoadingHistory] = useState(false);

    const [inputQuery, setInputQuery] = useState('');
    const [sidebarOpenMobile, setSidebarOpenMobile] = useState(false);

    // Sidebar stays hidden in the empty state until a conversation exists;
    // the header toggle can override that until the user starts a new chat.
    const [sidebarOverride, setSidebarOverride] = useState<boolean | null>(null);
    const [renamingInHeader, setRenamingInHeader] = useState(false);
    const [headerTitleDraft, setHeaderTitleDraft] = useState('');

    const turnsEndRef = useRef<HTMLDivElement>(null);

    const {
        sessions,
        activeSessionId,
        turnsBySession,
        pendingQuery,
        setActiveSession,
        createSession,
        rekeySession,
        renameSession,
        deleteSession,
        appendTurn,
        updateTurn,
        setPendingQuery,
        clearPendingQuery,
    } = useChatStore();

    const activeTurns = activeSessionId ? turnsBySession[activeSessionId] || [] : [];
    const activeSession = sessions.find((s) => s.id === activeSessionId);
    const sidebarVisible = sidebarOverride ?? Boolean(activeSessionId);

    // 1. Check user authentication state
    useEffect(() => {
        async function checkAuth() {
            try {
                const res = await authClient.getSession();
                if (res?.data?.user) {
                    setCurrentUser(res.data.user);
                } else {
                    setCurrentUser(null);
                }
            } catch (err) {
                console.error('Session check failed:', err);
                setCurrentUser(null);
            } finally {
                setAuthChecked(true);
            }
        }
        checkAuth();
    }, []);

    // 2. Fetch thread history from backend when activeSessionId changes and turns are not cached
    useEffect(() => {
        if (!activeSessionId || !currentUser) return;

        const cachedTurns = turnsBySession[activeSessionId];
        // If thread already has turns stored locally, skip remote fetch
        if (cachedTurns && cachedTurns.length > 0) return;

        async function loadHistory() {
            setIsLoadingHistory(true);
            try {
                const history = await fetchThreadHistory(activeSessionId!);
                if (history && Array.isArray(history.turns)) {
                    useChatStore.setState((state) => ({
                        turnsBySession: {
                            ...state.turnsBySession,
                            [activeSessionId!]: history.turns,
                        },
                    }));
                }
            } catch (err) {
                console.error('Failed to load thread history:', err);
            } finally {
                setIsLoadingHistory(false);
            }
        }

        loadHistory();
    }, [activeSessionId, currentUser]);

    // 3. Auto scroll down on new turns or step updates
    useEffect(() => {
        turnsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [activeTurns, isLoadingHistory]);

    const executeTurn = async ({
        query,
        action,
        editedQuery,
        forceNew = false,
    }: {
        query?: string;
        action?: 'approve' | 'reject' | 'edit';
        editedQuery?: string;
        forceNew?: boolean;
    }) => {
        let currentSessionId = forceNew ? null : activeSessionId;
        const turnId = `turn_${crypto.randomUUID()}`;

        const isResume = Boolean(action);
        // A brand-new conversation must not send a client-made thread_id: the backend
        // creates the real one and returns it on every event. We create a local temp
        // session for instant UI, then rekey it to the server id on the first event.
        let startedNewThread = false;

        if (!isResume) {
            if (!currentSessionId) {
                const tempThreadId = `temp_${crypto.randomUUID()}`;
                createSession(tempThreadId, query!);
                currentSessionId = tempThreadId;
                startedNewThread = true;
            }

            appendTurn(currentSessionId, {
                id: turnId,
                query: query!,
                status: 'streaming',
                progressSteps: [],
            });
        } else {
            const sessionTurns = useChatStore.getState().turnsBySession[currentSessionId!] || [];
            const targetTurn = sessionTurns[sessionTurns.length - 1];
            if (targetTurn) {
                updateTurn(currentSessionId!, targetTurn.id, {
                    status: 'streaming',
                    ...(action === 'edit' && editedQuery ? { query: editedQuery } : {}),
                });
            }
            return resumeTurn(currentSessionId!, targetTurn?.id || turnId, action!, editedQuery);
        }

        await runStream({
            query,
            threadId: startedNewThread ? null : currentSessionId!,
            localSessionId: currentSessionId!,
            turnId,
            startedNewThread,
        });
    };

    const resumeTurn = async (
        sessionId: string,
        turnId: string,
        action: 'approve' | 'reject' | 'edit',
        editedQuery?: string
    ) => {
        await runStream({ threadId: sessionId, action, editedQuery, localSessionId: sessionId, turnId });
    };

    const runStream = async ({
        query,
        threadId,
        action,
        editedQuery,
        localSessionId,
        turnId,
        startedNewThread = false,
    }: {
        query?: string;
        threadId: string | null;
        action?: 'approve' | 'reject' | 'edit';
        editedQuery?: string;
        localSessionId: string;
        turnId: string;
        startedNewThread?: boolean;
    }) => {
        let currentSessionId = localSessionId;
        let rekeyed = !startedNewThread;

        await streamResearch({
            query,
            threadId,
            action,
            editedQuery,
            onEvent: (event) => {
                if (event.thread_id && !rekeyed) {
                    rekeySession(currentSessionId, event.thread_id);
                    currentSessionId = event.thread_id;
                    rekeyed = true;
                } else if (event.thread_id && event.thread_id !== currentSessionId) {
                    currentSessionId = event.thread_id;
                }

                if (event.type === 'node_update') {
                    const nodeName = Object.keys(event.data || {})[0];
                    if (nodeName) {
                        const existingTurns =
                            useChatStore.getState().turnsBySession[currentSessionId] || [];
                        const currentTurn = existingTurns.find((t) => t.id === turnId);
                        const currentSteps = currentTurn?.progressSteps || [];
                        updateTurn(currentSessionId, turnId, {
                            progressSteps: [...currentSteps, nodeName],
                        });
                    }
                } else if (event.type === 'interrupted') {
                    updateTurn(currentSessionId, turnId, {
                        status: 'interrupted',
                        interrupt: event.interrupt,
                    });
                } else if (event.type === 'completed') {
                    const hasResponse = Boolean(event.response);
                    updateTurn(currentSessionId, turnId, {
                        status: hasResponse ? 'completed' : 'terminated',
                        response: event.response,
                        knowledgeSource: event.knowledge_source,
                        requiresExternalResearch: event.requires_external_research,
                        degraded: event.degraded,
                        terminationReason: event.termination_reason,
                    });
                } else if (event.type === 'error') {
                    updateTurn(currentSessionId, turnId, {
                        status: 'error',
                        error: event.error || event.detail || 'Server side failure during processing.',
                    });
                }
            },
            onError: (err) => {
                updateTurn(currentSessionId, turnId, {
                    status: 'error',
                    error: err?.message || 'Stream connection error',
                });
            },
        });
    };

    // Execute a query that was held back while the user signed in.
    useEffect(() => {
        if (!authChecked || !currentUser || !pendingQuery) return;

        const queryToSubmit = pendingQuery;
        clearPendingQuery();
        executeTurn({ query: queryToSubmit, forceNew: true });
    }, [authChecked, currentUser, pendingQuery]);

    const handleSend = async () => {
        if (!inputQuery.trim()) return;

        if (!currentUser) {
            setPendingQuery(inputQuery);
            setIsSignInOpen(true);
            return;
        }

        const q = inputQuery;
        setInputQuery('');
        await executeTurn({ query: q });
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const isThreadActive = Boolean(activeSessionId);

    const startNewChat = () => {
        setActiveSession(null);
        setSidebarOverride(null);
        setSidebarOpenMobile(false);
    };

    const startHeaderRename = () => {
        if (!activeSession) return;
        setHeaderTitleDraft(activeSession.title);
        setRenamingInHeader(true);
    };

    const saveHeaderRename = () => {
        if (activeSessionId && headerTitleDraft.trim()) {
            renameSession(activeSessionId, headerTitleDraft.trim());
        }
        setRenamingInHeader(false);
    };

    return (
        <div className="flex h-screen w-screen overflow-hidden bg-white text-neutral-900 dark:bg-[#0a0a0a] dark:text-neutral-100 font-inter antialiased">
            {/* Desktop Sidebar — hidden in the empty state until a conversation exists */}
            {sidebarVisible && (
                <div className="hidden md:block h-full shrink-0">
                    <AppSidebar
                        user={currentUser}
                        authChecked={authChecked}
                        onOpenSignIn={() => setIsSignInOpen(true)}
                        onNewChat={startNewChat}
                    />
                </div>
            )}

            {/* Mobile Sidebar Overlay Drawer */}
            {sidebarOpenMobile && (
                <div className="fixed inset-0 z-50 flex md:hidden">
                    <div
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm dark:bg-black/60"
                        onClick={() => setSidebarOpenMobile(false)}
                    />
                    <div className="relative z-10 h-full">
                        <AppSidebar
                            user={currentUser}
                            authChecked={authChecked}
                            onOpenSignIn={() => {
                                setSidebarOpenMobile(false);
                                setIsSignInOpen(true);
                            }}
                            onNewChat={startNewChat}
                        />
                    </div>
                </div>
            )}

            {/* Main Container */}
            <main className="flex flex-1 flex-col h-full overflow-hidden relative">
                {/* Top Header Bar */}
                <header className="flex h-12 shrink-0 items-center justify-between border-b border-neutral-200/80 px-4 font-inter text-xs text-neutral-500 dark:border-neutral-800/80 dark:text-neutral-400">
                    <div className="flex min-w-0 items-center gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSidebarOpenMobile(true)}
                            className="h-8 w-8 p-0 md:hidden text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-200"
                            aria-label="Open sidebar drawer"
                        >
                            <Menu className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSidebarOverride(!sidebarVisible)}
                            className="hidden md:flex h-8 w-8 p-0 text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-200"
                            aria-label={sidebarVisible ? 'Hide sidebar' : 'Show sidebar'}
                        >
                            {sidebarVisible ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeft className="h-4 w-4" />}
                        </Button>

                        {renamingInHeader && isThreadActive ? (
                            <div className="flex items-center gap-1">
                                <Input
                                    value={headerTitleDraft}
                                    onChange={(e) => setHeaderTitleDraft(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') saveHeaderRename();
                                        if (e.key === 'Escape') setRenamingInHeader(false);
                                    }}
                                    autoFocus
                                    aria-label="Rename conversation"
                                    className="h-7 w-48 border-neutral-300 bg-white text-xs text-neutral-900 focus-visible:ring-1 focus-visible:ring-neutral-400 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
                                />
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={saveHeaderRename}
                                    className="h-7 w-7 p-0 text-emerald-600 hover:bg-neutral-100 dark:text-emerald-400 dark:hover:bg-neutral-800"
                                    aria-label="Save conversation title"
                                >
                                    <Check className="h-3.5 w-3.5" />
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setRenamingInHeader(false)}
                                    className="h-7 w-7 p-0 text-neutral-500 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800"
                                    aria-label="Cancel rename"
                                >
                                    <X className="h-3.5 w-3.5" />
                                </Button>
                            </div>
                        ) : (
                            <span className="font-medium text-neutral-800 truncate max-w-[280px] dark:text-neutral-200">
                                {isThreadActive ? activeSession?.title || 'Research Session' : 'Lumen'}
                            </span>
                        )}

                        {isThreadActive && !renamingInHeader && (
                            <DropdownMenu>
                                <DropdownMenuTrigger
                                    className="inline-flex h-7 w-7 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-800 dark:text-neutral-500 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
                                    aria-label="Conversation options"
                                >
                                    <MoreHorizontal className="h-3.5 w-3.5" />
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="start" className="border-neutral-200 bg-white text-neutral-700 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-200">
                                    <DropdownMenuItem onClick={startHeaderRename}>
                                        <Pencil className="mr-2 h-3.5 w-3.5" /> Rename
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                        onClick={() => activeSessionId && deleteSession(activeSessionId)}
                                        className="text-red-600 focus:text-red-500 dark:text-red-400 dark:focus:text-red-300"
                                    >
                                        <Trash2 className="mr-2 h-3.5 w-3.5" /> Delete
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        )}
                    </div>

                    <div className="flex items-center gap-1">
                        <ThemeToggle />
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={startNewChat}
                            className="font-inter text-xs text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-200"
                        >
                            New chat
                        </Button>
                    </div>
                </header>

                {/* Dynamic View States */}
                {!isThreadActive ? (
                    /* Empty Default Landing State */
                    <div className="flex flex-1 flex-col items-center justify-center px-4 overflow-y-auto">
                        <div className="w-full max-w-[640px] space-y-6 text-center py-8">
                            <div className="space-y-2">
                                <h1 className="font-geist text-3xl md:text-4xl font-medium tracking-tighter text-neutral-900 dark:text-neutral-100">
                                    Lumen
                                </h1>
                                <p className="font-inter text-xs md:text-sm text-neutral-500 dark:text-neutral-400">
                                    Deep multi-agent research pipeline with real-time verification.
                                </p>
                            </div>

                            <div className="relative rounded-2xl border border-neutral-200 bg-neutral-50 p-2 transition-all duration-200 focus-within:border-neutral-400 focus-within:shadow-lg focus-within:ring-1 focus-within:ring-neutral-400 dark:border-neutral-800 dark:bg-neutral-900/50 dark:focus-within:border-neutral-600 dark:focus-within:ring-neutral-600">
                                <Textarea
                                    value={inputQuery}
                                    onChange={(e) => setInputQuery(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    placeholder="Ask a complex query to begin research..."
                                    aria-label="Research query"
                                    className="min-h-[70px] w-full resize-none border-0 bg-transparent font-inter text-sm text-neutral-900 placeholder:text-neutral-500 focus-visible:ring-0 focus-visible:ring-offset-0 dark:text-neutral-100 dark:placeholder:text-neutral-500"
                                />
                                <div className="flex items-center justify-between pt-1 px-1">
                                    <span className="font-inter text-[10px] text-neutral-500 dark:text-neutral-500">
                                        Press Enter to send, Shift+Enter for new line
                                    </span>
                                    <Button
                                        size="sm"
                                        onClick={handleSend}
                                        disabled={!inputQuery.trim()}
                                        className="h-7 w-7 rounded-lg bg-neutral-900 p-0 text-white hover:bg-neutral-700 disabled:opacity-30 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-200"
                                        aria-label="Send message"
                                    >
                                        <ArrowUp className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                ) : (
                    /* Active Thread Container with Scroll Bounds */
                    <div className="flex flex-1 flex-col h-full min-h-0 overflow-hidden">
                        <div className="flex-1 min-h-0">
                            <ScrollArea className="h-full px-4">
                                <div className="mx-auto max-w-[760px] py-6 space-y-2">
                                    {isLoadingHistory ? (
                                        <div className="flex items-center justify-center py-12 text-xs text-neutral-500 gap-2 dark:text-neutral-500">
                                            <Loader2 className="h-4 w-4 animate-spin text-neutral-400 dark:text-neutral-400" />
                                            Fetching thread history...
                                        </div>
                                    ) : (
                                        activeTurns.map((turn) => (
                                            <TurnView
                                                key={turn.id}
                                                turn={turn}
                                                onResume={(action, editedQuery) =>
                                                    executeTurn({ action, editedQuery })
                                                }
                                                onRetry={() => executeTurn({ query: turn.query })}
                                            />
                                        ))
                                    )}
                                    <div ref={turnsEndRef} />
                                </div>
                            </ScrollArea>
                        </div>

                        {/* Input Bar Pinned Bottom */}
                        <div className="shrink-0 border-t border-neutral-200/80 bg-white p-4 dark:border-neutral-800/80 dark:bg-[#0a0a0a]">
                            <div className="mx-auto max-w-[760px]">
                                <div className="relative rounded-xl border border-neutral-200 bg-neutral-50 p-2 transition-all focus-within:border-neutral-400 focus-within:shadow-md dark:border-neutral-800 dark:bg-neutral-900/50 dark:focus-within:border-neutral-600">
                                    <Textarea
                                        value={inputQuery}
                                        onChange={(e) => setInputQuery(e.target.value)}
                                        onKeyDown={handleKeyDown}
                                        placeholder="Send a follow-up query..."
                                        aria-label="Follow-up query"
                                        className="min-h-[50px] max-h-[160px] w-full resize-none border-0 bg-transparent font-inter text-sm text-neutral-900 placeholder:text-neutral-500 focus-visible:ring-0 focus-visible:ring-offset-0 dark:text-neutral-100 dark:placeholder:text-neutral-500"
                                    />
                                    <div className="flex justify-end pt-1">
                                        <Button
                                            size="sm"
                                            onClick={handleSend}
                                            disabled={!inputQuery.trim()}
                                            className="h-7 w-7 rounded-lg bg-neutral-900 p-0 text-white hover:bg-neutral-700 disabled:opacity-30 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-200"
                                            aria-label="Send follow-up message"
                                        >
                                            <ArrowUp className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </main>

            <SignInDialog open={isSignInOpen} onOpenChange={setIsSignInOpen} />
        </div>
    );
}