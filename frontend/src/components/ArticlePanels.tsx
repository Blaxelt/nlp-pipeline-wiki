export interface ArticlePanelsProps {
    articleText: string;
    iframeSrc: string;
    handleTextSelection: () => void;
}

export function ArticlePanels({
    articleText,
    iframeSrc,
    handleTextSelection
}: ArticlePanelsProps) {
    return (
        <div className="panels">
            <div
                className="clean-panel"
                onMouseUp={handleTextSelection}>
                <p style={{ whiteSpace: 'pre-wrap' }}>{articleText}</p>
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
