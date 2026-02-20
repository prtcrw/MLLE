import React, {useState} from 'react';
import './styles/plot_performance.css';
import {convertEnglishToSparql, ConvertResult} from '../../services/api';

const NaturalLanguageQuery: React.FC = () => {
    const [input, setInput] = useState('');
    const [sparql, setSparql] = useState('');
    const [results, setResults] = useState<Record<string, string | null>[]>([]);
    const [execError, setExecError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleConvert = async () => {
        setError(null);
        setExecError(null);
        setSparql('');
        setResults([]);
        setLoading(true);
        try {
            const res: ConvertResult = await convertEnglishToSparql(input);
            setSparql(res.sparql);
            setResults(res.results);
            if (res.error) setExecError(res.error);
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

    // Derive column headers from result keys
    const columns = results.length > 0 ? Object.keys(results[0]) : [];

    // Shorten long IRIs for display
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
                <textarea
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    placeholder="Describe the query in English..."
                    rows={6}
                    style={{width: '100%', fontFamily: 'monospace'}}
                />

                <div style={{display: 'flex', gap: '0.5rem'}}>
                    <button onClick={handleConvert} disabled={loading || !input.trim()}>Convert</button>
                    <button onClick={() => { setInput(''); setSparql(''); setResults([]); setError(null); setExecError(null); }}>Clear</button>
                </div>

                {loading && <div>Converting…</div>}
                {error && <div style={{color: 'red'}}>Error: {error}</div>}

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

                {execError && (
                    <div style={{color: 'orange', marginTop: '0.5rem'}}>
                        Query execution warning: {execError}
                    </div>
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

                {sparql && results.length === 0 && !loading && !execError && (
                    <div style={{marginTop: '0.5rem', color: '#888'}}>No results returned.</div>
                )}
            </div>
        </div>
    )
}

export default NaturalLanguageQuery;
