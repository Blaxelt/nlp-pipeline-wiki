import { useMemo } from 'react';

export interface Entity {
    text: string;
    title: string;
    url: string;
}

export interface ArticlePanelsProps {
    articleText: string;
    iframeSrc: string;
    handleTextSelection: () => void;
    entities?: Entity[];
}

function escapeRegExp(string: string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
}

export function ArticlePanels({
    articleText,
    iframeSrc,
    handleTextSelection,
    entities = []
}: ArticlePanelsProps) {

    const renderedText = useMemo(() => {
        if (!articleText) return null;
        if (!entities || entities.length === 0) return articleText;

        // Filter out whitespace-only entities to prevent matching every space
        const validEntities = entities.filter(e => e.text && e.text.trim().length > 0);
        if (validEntities.length === 0) return articleText;

        // Deduplicate by text, then also index by title for broader matching.
        // Priority by length - longest first so longer matches take precedence in regex alternation.
        const sortedEntities = [...validEntities].sort((a, b) => b.text.length - a.text.length);

        const entityMap = new Map<string, Entity>();
        const seenKeys = new Set<string>();
        for (const ent of sortedEntities) {
            for (const key of [ent.text, ent.title]) {
                if (key && key.trim().length > 0 && !seenKeys.has(key)) {
                    seenKeys.add(key);
                    entityMap.set(key, ent);
                }
            }
        }

        // Regex splitting - single alternation regex with capturing group
        // Sort pattern keys longest-first so regex prefers longer matches
        const pattern = Array.from(entityMap.keys())
            .sort((a, b) => b.length - a.length)
            .map(escapeRegExp)
            .join('|');
        if (!pattern) return articleText;

        // Full word boundary: entity must not be preceded or followed by a letter/number/underscore.
        const regex = new RegExp(`(?<![\\p{L}\\p{N}_])(${pattern})(?![\\p{L}\\p{N}_])`, 'gu');

        // This split preserves the matched entities, everything else is split around them
        const parts = articleText.split(regex);

        return parts.map((part, index) => {
            const ent = entityMap.get(part);
            if (ent) {
                return (
                    <strong
                        key={index}
                        className="cursor-pointer text-[#0066cc]"
                        onClick={() => window.open(ent.url, '_blank', 'noopener,noreferrer')}
                        title={ent.title}
                    >
                        {part}
                    </strong>
                );
            }
            return part; // normal text part
        });
    }, [articleText, entities]);

    return (
        <div className="flex h-screen w-screen overflow-hidden">
            <div
                className="w-1/2 p-5 overflow-y-auto"
                onMouseUp={handleTextSelection}>
                <p className="whitespace-pre-wrap">{renderedText}</p>
            </div>

            <div className="w-1/2 h-full p-5">
                <iframe
                    src={iframeSrc}
                    className="w-full h-full border-none"
                    title="Wikipedia Article"
                />
            </div>
        </div>
    )
}
