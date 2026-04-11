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

        // Priority by length - longest first
        const sortedEntities = [...validEntities].sort((a, b) => b.text.length - a.text.length);

        // Map lookup - O(1) matching
        const entityMap = new Map<string, Entity>();
        for (const ent of sortedEntities) {
            if (!entityMap.has(ent.text)) {
                entityMap.set(ent.text, ent);
            }
        }

        // Regex splitting - single alternation regex with capturing group
        const pattern = Array.from(entityMap.keys()).map(escapeRegExp).join('|');
        if (!pattern) return articleText;

        // Only check left boundary: entity must not be preceded by a letter/number/underscore.
        // No right boundary check, so "valle" matches inside "valles" ([[valle]]s wikitext pattern).
        const regex = new RegExp(`(?<![\\p{L}\\p{N}_])(${pattern})`, 'gu');

        // This split preserves the matched entities, everything else is split around them
        const parts = articleText.split(regex);

        return parts.map((part, index) => {
            const ent = entityMap.get(part);
            if (ent) {
                return (
                    <strong
                        key={index}
                        style={{ cursor: 'pointer', color: '#0066cc' }}
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
        <div className="panels">
            <div
                className="clean-panel"
                onMouseUp={handleTextSelection}>
                <p style={{ whiteSpace: 'pre-wrap' }}>{renderedText}</p>
            </div>

            <div className="original-panel">
                <iframe
                    src={iframeSrc}
                    className="original-iframe"
                    title="Wikipedia Article"
                />
            </div>
        </div>
    )
}
