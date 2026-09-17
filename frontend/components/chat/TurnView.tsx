'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Turn } from '@/store/useChatStore';
import { ProgressIndicator } from './ProgressIndicator';
import { ApprovalCard } from './ApprovalCard';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp, AlertCircle, RefreshCw } from 'lucide-react';

interface TurnViewProps {
    turn: Turn;
    onResume: (action: 'approve' | 'reject' | 'edit', editedQuery?: string) => void;
    onRetry?: () => void;
}

export function TurnView({ turn, onResume, onRetry }: TurnViewProps) {
    const [showDetails, setShowDetails] = useState(false);

    const isStreaming = turn.status === 'streaming';
    const hasMetadata = Boolean(
        turn.knowledgeSource || turn.requiresExternalResearch !== undefined || turn.degraded
    );

    return (
        <div className="space-y-4 py-4 font-inter">
            {/* User Query */}
            <div className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl bg-neutral-900 px-4 py-2.5 text-sm text-white dark:bg-neutral-800/80 dark:text-neutral-100">
                    {turn.query}
                </div>
            </div>

            {/* Lumen Response Block */}
            <div className="flex gap-3">
                {/* Wordmark Indicator */}
                <div className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded border border-neutral-300 bg-neutral-100 font-geist text-[10px] font-medium tracking-tighter text-neutral-600 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-300">
                    L
                </div>

                <div className="min-w-0 flex-1 space-y-3">
                    {/* Real progress streaming indicator */}
                    {(isStreaming || turn.progressSteps.length > 0) && (
                        <ProgressIndicator steps={turn.progressSteps} isStreaming={isStreaming} />
                    )}

                    {/* Interrupted Human-in-the-loop Card */}
                    {turn.status === 'interrupted' && (
                        <ApprovalCard
                            originalQuery={turn.query}
                            interruptPayload={turn.interrupt}
                            onApprove={() => onResume('approve')}
                            onReject={() => onResume('reject')}
                            onEditSubmit={(q) => onResume('edit', q)}
                            isStreaming={isStreaming}
                        />
                    )}

                    {/* Error State */}
                    {turn.status === 'error' && (
                        <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-300">
                            <div className="flex items-center gap-2">
                                <AlertCircle className="h-4 w-4 shrink-0 text-red-600 dark:text-red-400" />
                                <span>{turn.error || 'An unexpected error occurred during execution.'}</span>
                            </div>
                            {onRetry && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={onRetry}
                                    className="h-7 px-2 font-inter text-xs text-red-700 hover:bg-red-100 hover:text-red-800 dark:text-red-300 dark:hover:bg-red-900/30 dark:hover:text-red-200"
                                >
                                    <RefreshCw className="mr-1 h-3 w-3" /> Retry
                                </Button>
                            )}
                        </div>
                    )}

                    {/* Terminated State */}
                    {turn.status === 'terminated' && turn.terminationReason && (
                        <div className="rounded-lg border border-neutral-200 bg-neutral-100 p-3.5 text-xs leading-relaxed text-neutral-600 dark:border-neutral-800 dark:bg-neutral-900/40 dark:text-neutral-400">
                            <span className="font-medium text-neutral-800 dark:text-neutral-300">Run Ended: </span>
                            {turn.terminationReason}
                        </div>
                    )}

                    {/* Clean Formatted Markdown Output */}
                    {turn.response && (
                        <div className="animate-in fade-in slide-in-from-bottom-1 duration-300 text-sm leading-relaxed text-neutral-800 dark:text-neutral-200">
                            <ReactMarkdown
                                components={{
                                    h1: ({ children }) => (
                                        <h1 className="font-geist text-lg font-medium tracking-tighter text-neutral-900 dark:text-neutral-100 mt-4 mb-2">
                                            {children}
                                        </h1>
                                    ),
                                    h2: ({ children }) => (
                                        <h2 className="font-geist text-base font-medium tracking-tighter text-neutral-900 dark:text-neutral-100 mt-3 mb-1.5">
                                            {children}
                                        </h2>
                                    ),
                                    h3: ({ children }) => (
                                        <h3 className="font-geist text-sm font-medium tracking-tighter text-neutral-900 dark:text-neutral-200 mt-2 mb-1">
                                            {children}
                                        </h3>
                                    ),
                                    p: ({ children }) => <p className="mb-2 leading-relaxed">{children}</p>,
                                    strong: ({ children }) => (
                                        <strong className="font-medium text-neutral-900 dark:text-neutral-100">{children}</strong>
                                    ),
                                    em: ({ children }) => (
                                        <em className="italic text-neutral-600 dark:text-neutral-300">{children}</em>
                                    ),
                                    ul: ({ children }) => (
                                        <ul className="list-disc list-inside space-y-1 my-2 pl-2 text-neutral-700 dark:text-neutral-300">
                                            {children}
                                        </ul>
                                    ),
                                    ol: ({ children }) => (
                                        <ol className="list-decimal list-inside space-y-1 my-2 pl-2 text-neutral-700 dark:text-neutral-300">
                                            {children}
                                        </ol>
                                    ),
                                    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                                    code: ({ children }) => (
                                        <code className="rounded border border-neutral-200 bg-neutral-100 px-1.5 py-0.5 font-inter text-xs text-neutral-700 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-300">
                                            {children}
                                        </code>
                                    ),
                                    pre: ({ children }) => (
                                        <pre className="my-3 overflow-x-auto rounded-lg border border-neutral-200 bg-neutral-50 p-3 font-inter text-xs text-neutral-700 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-300">
                                            {children}
                                        </pre>
                                    ),
                                    blockquote: ({ children }) => (
                                        <blockquote className="border-l-2 border-neutral-300 pl-3 my-2 text-neutral-500 italic dark:border-neutral-700 dark:text-neutral-400">
                                            {children}
                                        </blockquote>
                                    ),
                                }}
                            >
                                {turn.response}
                            </ReactMarkdown>
                        </div>
                    )}

                    {/* Collapsible Metadata Section */}
                    {turn.status === 'completed' && hasMetadata && (
                        <div className="pt-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setShowDetails(!showDetails)}
                                className="h-6 px-0 font-inter text-[11px] text-neutral-500 hover:bg-transparent hover:text-neutral-800 dark:hover:text-neutral-300"
                                aria-label={showDetails ? 'Hide execution metadata' : 'Show execution metadata'}
                            >
                                {showDetails ? (
                                    <>
                                        <ChevronUp className="mr-1 h-3 w-3" /> Hide Details
                                    </>
                                ) : (
                                    <>
                                        <ChevronDown className="mr-1 h-3 w-3" /> View Details
                                    </>
                                )}
                            </Button>

                            {showDetails && (
                                <div className="mt-2 space-y-1 rounded-md border border-neutral-200/60 bg-neutral-50 p-2.5 font-inter text-[11px] text-neutral-600 dark:border-neutral-800/60 dark:bg-neutral-950/50 dark:text-neutral-400">
                                    {turn.knowledgeSource && (
                                        <div>
                                            <span className="text-neutral-500">Knowledge Source:</span> {turn.knowledgeSource}
                                        </div>
                                    )}
                                    {turn.requiresExternalResearch !== undefined && (
                                        <div>
                                            <span className="text-neutral-500">External Research Required:</span>{' '}
                                            {turn.requiresExternalResearch ? 'Yes' : 'No'}
                                        </div>
                                    )}
                                    {turn.degraded && (
                                        <div className="text-amber-700 dark:text-amber-400/90">
                                            <span>Execution note:</span> Operating in fallback/degraded mode
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
