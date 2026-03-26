import React, {ReactNode, useEffect, useState} from 'react';
import './styles/plot_performance.css';
import {getSettings, listSettingsRepos, NLQResponse, queryNaturalLanguage} from '../../services/api';
import {DownloadIcon} from '../../components/Icons';

type ResultValue = string | null | string[];
type ResultRow = Record<string, ResultValue>;
const NLQ_STORAGE_KEY = 'mllo:nlq-state';

const inlineCodeStyle: React.CSSProperties = {
    fontFamily: 'monospace',
    background: '#f1f3f5',
    padding: '0.1rem 0.3rem',
    borderRadius: '4px',
};

const renderInlineMarkdown = (text: string): ReactNode[] => {
    const nodes: ReactNode[] = [];
    const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g;
    let lastIndex = 0;
    let key = 0;
    for (const match of text.matchAll(pattern)) {
        const start = match.index ?? 0;
        if (start > lastIndex) {
            nodes.push(text.slice(lastIndex, start));
        }
        const token = match[0];
        if (token.startsWith('**') && token.endsWith('**')) {
            nodes.push(<strong key={`b-${key++}`}>{token.slice(2, -2)}</strong>);
        } else if (token.startsWith('`') && token.endsWith('`')) {
            nodes.push(<code key={`c-${key++}`} style={inlineCodeStyle}>{token.slice(1, -1)}</code>);
        }
        lastIndex = start + token.length;
    }
    if (lastIndex < text.length) {
        nodes.push(text.slice(lastIndex));
    }
    return nodes.length > 0 ? nodes : [text];
};

const isMarkdownSeparator = (line: string): boolean => /^\s*\|?[\s:-]+\|[\s|:-]*$/.test(line);

const parseTableRow = (line: string): string[] =>
    line
        .trim()
        .replace(/^\|/, '')
        .replace(/\|$/, '')
        .split('|')
        .map((cell) => cell.trim());

const renderMarkdownAnswer = (text: string): ReactNode => {
    const lines = text.split(/\r?\n/);
    const blocks: ReactNode[] = [];
    let i = 0;

    while (i < lines.length) {
        if (!lines[i].trim()) {
            i += 1;
            continue;
        }

        if (
            i + 1 < lines.length &&
            lines[i].includes('|') &&
            isMarkdownSeparator(lines[i + 1])
        ) {
            const headers = parseTableRow(lines[i]);
            const rows: string[][] = [];
            i += 2;
            while (i < lines.length && lines[i].includes('|') && lines[i].trim()) {
                rows.push(parseTableRow(lines[i]));
                i += 1;
            }
            blocks.push(
                <div key={`table-${blocks.length}`} style={{overflowX: 'auto', margin: '0.75rem 0'}}>
                    <table style={{width: '100%', borderCollapse: 'collapse'}}>
                        <thead>
                            <tr>
                                {headers.map((header, index) => (
                                    <th key={index} style={{border: '1px solid #d7d7d7', padding: '0.55rem', background: '#f5f5f5', textAlign: 'left'}}>
                                        {renderInlineMarkdown(header)}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((row, rowIndex) => (
                                <tr key={rowIndex}>
                                    {headers.map((_, colIndex) => (
                                        <td key={colIndex} style={{border: '1px solid #e7e7e7', padding: '0.55rem', verticalAlign: 'top'}}>
                                            {renderInlineMarkdown(row[colIndex] ?? '')}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            );
            continue;
        }

        if (/^\s*[-*]\s+/.test(lines[i])) {
            const items: string[] = [];
            while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
                items.push(lines[i].replace(/^\s*[-*]\s+/, '').trim());
                i += 1;
            }
            blocks.push(
                <ul key={`list-${blocks.length}`} style={{margin: '0.5rem 0 1rem 1.25rem'}}>
                    {items.map((item, index) => (
                        <li key={index} style={{marginBottom: '0.35rem'}}>{renderInlineMarkdown(item)}</li>
                    ))}
                </ul>
            );
            continue;
        }

        const paragraphLines: string[] = [];
        while (
            i < lines.length &&
            lines[i].trim() &&
            !(i + 1 < lines.length && lines[i].includes('|') && isMarkdownSeparator(lines[i + 1])) &&
            !/^\s*[-*]\s+/.test(lines[i])
        ) {
            paragraphLines.push(lines[i].trim());
            i += 1;
        }
        blocks.push(
            <p key={`p-${blocks.length}`} style={{margin: '0 0 0.85rem', lineHeight: 1.55}}>
                {renderInlineMarkdown(paragraphLines.join(' '))}
            </p>
        );
    }

    return <div>{blocks}</div>;
};

const normalizeCellLines = (value: ResultValue): string[] => {
    if (value == null) return [];
    if (Array.isArray(value)) return value.map((item) => String(item));
    return [String(value)];
};

const shortenValue = (val: string): string => {
    const hashIdx = val.lastIndexOf('#');
    if (hashIdx >= 0) return val.substring(hashIdx + 1);
    const slashIdx = val.lastIndexOf('/');
    if (slashIdx >= 0 && slashIdx < val.length - 1) return val.substring(slashIdx + 1);
    return val;
};

const csvEscape = (value: string): string => `"${value.replace(/"/g, '""')}"`;

const downloadCsv = (rows: ResultRow[], columns: string[]): void => {
    const lines = [
        columns.map(csvEscape).join(','),
        ...rows.map((row) =>
            columns
                .map((column) => csvEscape(normalizeCellLines(row[column]).join(' | ')))
                .join(',')
        ),
    ];
    const blob = new Blob([lines.join('\n')], {type: 'text/csv;charset=utf-8;'});
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', 'nlq_results.csv');
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
};

interface PersistedNLQState {
    input: string;
    sparql: string;
    results: ResultRow[];
    answer: string;
    showSparql: boolean;
    selectedRepo: string;
    answerMode: 'exact' | 'conceptual' | 'auto';
    metadata: {repo_used: string; inference_used: boolean} | null;
    debugInfo: {tool: string; reasoning: string} | null;
}

const NaturalLanguageQuery: React.FC = () => {
    const [input, setInput] = useState('');
    const [sparql, setSparql] = useState('');
    const [results, setResults] = useState<ResultRow[]>([]);
    const [answer, setAnswer] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showSparql, setShowSparql] = useState(false);
    const [repos, setRepos] = useState<string[]>([]);
    const [selectedRepo, setSelectedRepo] = useState('');
    const [answerMode, setAnswerMode] = useState<'exact' | 'conceptual' | 'auto'>('auto');
    const [metadata, setMetadata] = useState<{repo_used: string; inference_used: boolean} | null>(null);
    const [debugInfo, setDebugInfo] = useState<{tool: string; reasoning: string} | null>(null);
    const [hasRestoredState, setHasRestoredState] = useState(false);
    const examplePrompts = [
        'Get all pipelines.',
        'Show me models with performance more than 0.9.'
    ];

    useEffect(() => {
        const load = async () => {
            try {
                const [settings, availableRepos] = await Promise.all([
                    getSettings(),
                    listSettingsRepos().catch(() => []),
                ]);
                setAnswerMode(settings.answer_mode);
                setSelectedRepo(settings.graphdb_default_repo);
                setRepos(availableRepos.length > 0 ? availableRepos : [settings.graphdb_default_repo]);
            } catch (err) {
                setError((err as Error).message);
            }
        };
        void load();
    }, []);

    useEffect(() => {
        try {
            const rawState = window.sessionStorage.getItem(NLQ_STORAGE_KEY);
            if (!rawState) {
                setHasRestoredState(true);
                return;
            }

            const persistedState = JSON.parse(rawState) as PersistedNLQState;
            setInput(persistedState.input ?? '');
            setSparql(persistedState.sparql ?? '');
            setResults(Array.isArray(persistedState.results) ? persistedState.results : []);
            setAnswer(persistedState.answer ?? '');
            setShowSparql(Boolean(persistedState.showSparql));
            if (persistedState.selectedRepo) {
                setSelectedRepo(persistedState.selectedRepo);
            }
            if (persistedState.answerMode) {
                setAnswerMode(persistedState.answerMode);
            }
            setMetadata(persistedState.metadata ?? null);
            setDebugInfo(persistedState.debugInfo ?? null);
        } catch {
            window.sessionStorage.removeItem(NLQ_STORAGE_KEY);
        } finally {
            setHasRestoredState(true);
        }
    }, []);

    useEffect(() => {
        if (!hasRestoredState) {
            return;
        }

        const stateToPersist: PersistedNLQState = {
            input,
            sparql,
            results,
            answer,
            showSparql,
            selectedRepo,
            answerMode,
            metadata,
            debugInfo,
        };

        window.sessionStorage.setItem(NLQ_STORAGE_KEY, JSON.stringify(stateToPersist));
    }, [answer, answerMode, debugInfo, hasRestoredState, input, metadata, results, selectedRepo, showSparql, sparql]);

    const clearResults = () => {
        setSparql('');
        setResults([]);
        setAnswer('');
        setMetadata(null);
        setDebugInfo(null);
    };

    const handleConvert = async () => {
        setError(null);
        clearResults();
        setLoading(true);
        try {
            const res: NLQResponse = await queryNaturalLanguage(input, selectedRepo, answerMode);
            setSparql(res.sparql);
            setResults(res.results);
            setAnswer(res.answer);
            setMetadata({repo_used: res.repo_used, inference_used: res.inference_used});
            setDebugInfo({tool: res.intent.tool, reasoning: res.intent.reasoning});
        } catch (err: any) {
            setError(err.message || String(err));
        } finally {
            setLoading(false);
        }
    };

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(sparql);
        } catch (e) {
            // ignore
        }
    };

    const columns = results.length > 0 ? Object.keys(results[0]) : [];

    return (
        <div className="page-container">
            <h2>LLM Query</h2>
            <p>Enter a natural-language description and convert it to SPARQL using your configured LLM endpoint.</p>

            <div style={{display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
                <div style={{display: 'flex', flexDirection: 'column', gap: '0.35rem'}}>
                    <label style={{fontSize: '0.9rem'}}>Examples</label>
                    <div style={{display: 'flex', flexWrap: 'wrap', gap: '0.4rem'}}>
                        {examplePrompts.map((prompt) => (
                            <button
                                key={prompt}
                                type="button"
                                onClick={() => setInput(prompt)}
                                disabled={loading}
                                style={{fontSize: '0.82rem'}}
                            >
                                {prompt}
                            </button>
                        ))}
                    </div>
                </div>

                <div style={{display: 'flex', gap: '0.5rem', flexWrap: 'wrap'}}>
                    <label style={{display: 'flex', flexDirection: 'column', minWidth: '220px'}}>
                        Repository
                        <select value={selectedRepo} onChange={(e) => setSelectedRepo(e.target.value)}>
                            {repos.map((repo) => (
                                <option key={repo} value={repo}>{repo}</option>
                            ))}
                        </select>
                    </label>
                    <label style={{display: 'flex', flexDirection: 'column', minWidth: '220px'}}>
                        Answer Mode
                        <select value={answerMode} onChange={(e) => setAnswerMode(e.target.value as 'exact' | 'conceptual' | 'auto')}>
                            <option value="exact">Exact</option>
                            <option value="conceptual">Conceptual</option>
                            <option value="auto">Auto</option>
                        </select>
                    </label>
                </div>

                <textarea
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    placeholder="Describe the query in English..."
                    rows={6}
                    style={{width: '100%', fontFamily: 'monospace'}}
                />

                <div style={{display: 'flex', gap: '0.5rem', flexWrap: 'wrap'}}>
                    <button onClick={handleConvert} disabled={loading || !input.trim()}>Convert</button>
                    <button onClick={() => {
                        setInput('');
                        setError(null);
                        clearResults();
                        window.sessionStorage.removeItem(NLQ_STORAGE_KEY);
                    }}>Clear</button>
                </div>

                {loading && <div>Converting…</div>}
                {error && <div style={{color: 'red'}}>Error: {error}</div>}

                {metadata && (
                    <div style={{display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.9rem'}}>
                        <span>Repository: <strong>{metadata.repo_used}</strong></span>
                        <span>Inference: <strong>{metadata.inference_used ? 'On' : 'Off'}</strong></span>
                    </div>
                )}

                {answer && (
                    <div style={{marginTop: '0.5rem'}}>
                        <label>Answer</label>
                        <div style={{padding: '0.9rem', background: '#f7f7f7', border: '1px solid #ddd', overflowX: 'auto'}}>
                            {renderMarkdownAnswer(answer)}
                        </div>
                    </div>
                )}

                <div style={{display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
                    <button
                        onClick={() => setShowSparql(!showSparql)}
                        disabled={!sparql}
                        style={{alignSelf: 'flex-start'}}
                    >
                        {showSparql ? 'Hide SPARQL Query' : 'Show SPARQL Query'}
                    </button>

                    {showSparql && (
                        <>
                            <label>SPARQL query</label>
                            <textarea
                                value={sparql}
                                readOnly
                                rows={10}
                                style={{width: '100%', fontFamily: 'monospace'}}
                            />
                            <div style={{display: 'flex', gap: '0.5rem'}}>
                                <button onClick={handleCopy} disabled={!sparql}>Copy</button>
                            </div>
                        </>
                    )}
                </div>

                {debugInfo && (
                    <details>
                        <summary>Debug Info</summary>
                        <div style={{marginTop: '0.5rem'}}>
                            <div><strong>Intent Tool:</strong> {debugInfo.tool}</div>
                            <div><strong>Reasoning:</strong> {debugInfo.reasoning}</div>
                        </div>
                    </details>
                )}

                {results.length > 0 && (
                    <div style={{marginTop: '1rem'}}>
                        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap'}}>
                            <label>Query Results ({results.length} row{results.length !== 1 ? 's' : ''})</label>
                            <button
                                type="button"
                                onClick={() => downloadCsv(results, columns)}
                                style={{display: 'inline-flex', alignItems: 'center', gap: '0.35rem'}}
                            >
                                <DownloadIcon width={16} height={16}/>
                                Export CSV
                            </button>
                        </div>
                        <div style={{overflowX: 'auto', marginTop: '0.5rem'}}>
                            <table style={{width: '100%', minWidth: 'max-content', borderCollapse: 'collapse', fontFamily: 'monospace', fontSize: '0.85rem'}}>
                                <thead>
                                    <tr>
                                        {columns.map(col => (
                                            <th key={col} style={{
                                                border: '1px solid #ccc',
                                                padding: '6px 10px',
                                                background: '#f5f5f5',
                                                textAlign: 'left',
                                                whiteSpace: 'nowrap',
                                            }}>
                                                {col}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {results.map((row, i) => (
                                        <tr key={i}>
                                            {columns.map(col => (
                                                <td key={col} style={{
                                                    border: '1px solid #eee',
                                                    padding: '8px 10px',
                                                    maxWidth: '520px',
                                                    whiteSpace: 'normal',
                                                    wordBreak: 'break-word',
                                                    verticalAlign: 'top',
                                                }}>
                                                    <div style={{display: 'flex', flexDirection: 'column', gap: '0.2rem'}}>
                                                        {normalizeCellLines(row[col]).map((line, index) => (
                                                            <span key={index} title={line}>{shortenValue(line)}</span>
                                                        ))}
                                                    </div>
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {sparql && results.length === 0 && !loading && !error && (
                    <div style={{marginTop: '0.5rem', color: '#888'}}>No results returned.</div>
                )}
            </div>
        </div>
    );
}

export default NaturalLanguageQuery;
