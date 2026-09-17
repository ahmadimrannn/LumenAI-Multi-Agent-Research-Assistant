'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Loader2, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';

const NODE_NAME_MAP: Record<string, string> = {
    query_classifier: 'Classifying query',
    researcher: 'Researching sources',
    source_critic: 'Evaluating source quality',
    evidence_extractor: 'Extracting key evidence',
    conflicts_analyst: 'Analyzing conflicts & edge cases',
    report_writer: 'Writing final report',
    human_approval: 'Awaiting human review',
    direct_knowledge_agent: 'Processing direct response',
};

interface ProgressIndicatorProps {
    steps: string[];
    isStreaming: boolean;
}

export function ProgressIndicator({ steps, isStreaming }: ProgressIndicatorProps) {
    const [expanded, setExpanded] = useState(false);

    if (steps.length === 0 && !isStreaming) return null;

    const currentStepRaw = steps[steps.length - 1];
    const currentStepLabel = currentStepRaw
        ? NODE_NAME_MAP[currentStepRaw] || currentStepRaw.replace(/_/g, ' ')
        : 'Initializing analysis...';

    return (
        <div className="my-3 rounded-lg border border-neutral-200 bg-neutral-50 p-3 font-inter text-xs text-neutral-500 dark:border-neutral-800 dark:bg-neutral-950/40 dark:text-neutral-400">
            {/* Header bar */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                    {isStreaming ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-neutral-600 dark:text-neutral-300" />
                    ) : (
                        <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-500" />
                    )}
                    <span className={isStreaming ? 'font-medium text-neutral-800 dark:text-neutral-200' : 'font-medium text-emerald-700 dark:text-emerald-400'}>
                        {isStreaming ? currentStepLabel : 'Pipeline complete'}
                    </span>
                    <span className="text-neutral-500 dark:text-neutral-500">
                        ({steps.length} {steps.length === 1 ? 'step' : 'steps'})
                    </span>
                </div>

                {steps.length > 0 && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setExpanded(!expanded)}
                        className="h-6 px-1.5 text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-200"
                        aria-label={expanded ? 'Collapse progress details' : 'Expand progress details'}
                    >
                        {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                    </Button>
                )}
            </div>

            {/* Expandable step list with green indicators on completion */}
            {expanded && steps.length > 0 && (
                <div className="mt-2.5 space-y-1.5 border-t border-neutral-200 pt-2.5 dark:border-neutral-800/80">
                    {steps.map((step, idx) => {
                        const isActiveStep = idx === steps.length - 1 && isStreaming;
                        const isCompletedStep = !isActiveStep;
                        const label = NODE_NAME_MAP[step] || step.replace(/_/g, ' ');

                        return (
                            <div key={idx} className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-2">
                                    <span className="font-inter text-[10px] text-neutral-400 dark:text-neutral-600">0{idx + 1}</span>
                                    <span
                                        className={
                                            isCompletedStep
                                                ? 'text-emerald-700 font-medium dark:text-emerald-400'
                                                : 'text-neutral-800 font-medium dark:text-neutral-200'
                                        }
                                    >
                                        {label}
                                    </span>
                                </div>

                                <div className="flex items-center gap-1.5">
                                    {isCompletedStep ? (
                                        <div className="flex items-center gap-1 text-[11px] font-medium text-emerald-700 dark:text-emerald-400">
                                            <span>Completed</span>
                                            <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-500" />
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-1 text-[11px] text-neutral-500 dark:text-neutral-400">
                                            <span>In progress</span>
                                            <Loader2 className="h-3 w-3 animate-spin text-neutral-600 dark:text-neutral-300" />
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}