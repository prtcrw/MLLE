import React, {useState} from 'react';
import './styles/plot_performance.css';
import {convertEnglishToSparql} from '../../services/api';

const NaturalLanguageQuery: React.FC = () => {
    const [input, setInput] = useState('');
    const [result, setResult] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleConvert = async () => {
        setError(null);
        setResult('');
        setLoading(true);
        try {
            const sparql = await convertEnglishToSparql(input);
            setResult(sparql);
        } catch (err: any) {
            setError(err.message || String(err));
        } finally {
            setLoading(false);
        }
    };

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(result);
        } catch (e) {
            // ignore
        }
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
                    <button onClick={() => { setInput(''); setResult(''); setError(null); }}>Clear</button>
                </div>

                {loading && <div>Converting…</div>}
                {error && <div style={{color: 'red'}}>Error: {error}</div>}

                <label>SPARQL result</label>
                <textarea
                    value={result}
                    readOnly
                    rows={10}
                    style={{width: '100%', fontFamily: 'monospace'}}
                />
                <div style={{display: 'flex', gap: '0.5rem'}}>
                    <button onClick={handleCopy} disabled={!result}>Copy</button>
                </div>
            </div>
        </div>
    )
}

export default NaturalLanguageQuery;
