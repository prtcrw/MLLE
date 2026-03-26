import React, {useEffect, useState} from 'react';
import './styles/plot_performance.css';
import {getSettings, listSettingsRepos, NLQResponse, queryNaturalLanguage} from '../../services/api';

const NaturalLanguageQuery: React.FC = () => {
    const [input, setInput] = useState('');
    const [sparql, setSparql] = useState('');
    const [results, setResults] = useState<Record<string, string | null>[]>([]);
    const [answer, setAnswer] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showSparql, setShowSparql] = useState(false);
    const [repos, setRepos] = useState<string[]>([]);
    const [selectedRepo, setSelectedRepo] = useState('');
    const [answerMode, setAnswerMode] = useState<'exact' | 'conceptual' | 'auto'>('auto');
    const [metadata, setMetadata] = useState<{repo_used: string; inference_used: boolean} | null>(null);
    const [debugInfo, setDebugInfo] = useState<{tool: string; reasoning: string} | null>(null);
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

    const shorten = (val: string | null): string => {
        if (val == null) return '';
        const hashIdx = val.lastIndexOf('#');
        if (hashIdx >= 0) return val.substring(hashIdx + 1);
        const slashIdx = val.lastIndexOf('/');
        if (slashIdx >= 0 && slashIdx < val.length - 1) return val.substring(slashIdx + 1);
        return val;
    };

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
                    <button onClick={() => { setInput(''); setError(null); clearResults(); }}>Clear</button>
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
                        <div style={{padding: '0.75rem', background: '#f7f7f7', border: '1px solid #ddd'}}>
                            {answer}
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
                        <label>Query Results ({results.length} row{results.length !== 1 ? 's' : ''})</label>
                        <div style={{overflowX: 'auto', marginTop: '0.5rem'}}>
                            <table style={{width: '100%', borderCollapse: 'collapse', fontFamily: 'monospace', fontSize: '0.85rem'}}>
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
                                                    padding: '4px 10px',
                                                    maxWidth: '400px',
                                                    overflow: 'hidden',
                                                    textOverflow: 'ellipsis',
                                                    whiteSpace: 'nowrap',
                                                }} title={row[col] ?? ''}>
                                                    {shorten(row[col])}
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
