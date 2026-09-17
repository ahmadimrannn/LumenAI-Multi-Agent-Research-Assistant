/* eslint-disable @typescript-eslint/no-explicit-any */
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface ApprovalCardProps {
    originalQuery: string;
    interruptPayload: any;
    onApprove: () => void;
    onReject: () => void;
    onEditSubmit: (newQuery: string) => void;
    isStreaming: boolean;
}

export function ApprovalCard({
    originalQuery,
    interruptPayload,
    onApprove,
    onReject,
    onEditSubmit,
    isStreaming,
}: ApprovalCardProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [editedQuery, setEditedQuery] = useState(originalQuery);

    const reasonText =
        typeof interruptPayload === 'string'
            ? interruptPayload
            : interruptPayload?.reason || interruptPayload?.message || 'Human input required to proceed.';

    return (
        <div className="my-4 rounded-xl border border-neutral-200 bg-neutral-50 p-4 font-inter text-neutral-800 shadow-sm transition-all duration-200 dark:border-neutral-800 dark:bg-neutral-900/60 dark:text-neutral-200">
            <div className="mb-2 text-xs font-medium uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
                Approval Requested
            </div>

            <p className="mb-4 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
                {reasonText}
            </p>

            {isEditing ? (
                <div className="space-y-3">
                    <Textarea
                        value={editedQuery}
                        onChange={(e) => setEditedQuery(e.target.value)}
                        disabled={isStreaming}
                        className="min-h-20 border-neutral-300 bg-white font-inter text-sm text-neutral-900 placeholder:text-neutral-500 focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 dark:border-neutral-700 dark:bg-neutral-950 dark:text-neutral-100"
                        placeholder="Edit query before resuming..."
                    />
                    <div className="flex items-center gap-2">
                        <Button
                            size="sm"
                            disabled={isStreaming || !editedQuery.trim()}
                            onClick={() => onEditSubmit(editedQuery)}
                            className="bg-neutral-900 font-inter text-xs text-white hover:bg-neutral-700 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-200"
                        >
                            Submit edited query
                        </Button>
                        <Button
                            size="sm"
                            variant="outline"
                            disabled={isStreaming}
                            onClick={() => setIsEditing(false)}
                            className="border-neutral-300 font-inter text-xs text-neutral-700 hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
                        >
                            Cancel
                        </Button>
                    </div>
                </div>
            ) : (
                <div className="flex flex-wrap items-center gap-2">
                    <Button
                        size="sm"
                        disabled={isStreaming}
                        onClick={onApprove}
                        className="bg-neutral-900 font-inter text-xs text-white hover:bg-neutral-700 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-neutral-200"
                    >
                        Approve
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        disabled={isStreaming}
                        onClick={onReject}
                        className="border-neutral-300 font-inter text-xs text-neutral-700 hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
                    >
                        Reject
                    </Button>
                    <Button
                        size="sm"
                        variant="ghost"
                        disabled={isStreaming}
                        onClick={() => setIsEditing(true)}
                        className="font-inter text-xs text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
                    >
                        Edit Query
                    </Button>
                </div>
            )}
        </div>
    );
}