import React, {useEffect, useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {
    getSettings,
    getNlqLogs,
    listSettingsRepos,
    MLLESettings,
    NlqLogEntry,
    saveSettings,
    testLlmConnection
} from '../../services/api';
import './styles/plot_performance.css';

const providerOptions = [
    {value: 'lm_studio', label: 'LM Studio'},
    {value: 'openai', label: 'OpenAI'},
    {value: 'anthropic', label: 'Anthropic'},
    {value: 'gemini', label: 'Gemini'},
];

const prettyJson = (value: unknown) => JSON.stringify(value, null, 2);

const llmCallForPurpose = (log: NlqLogEntry, purpose: string) =>
    log.llm_calls.find((call) => call.purpose === purpose);

const llmCallsForPurposes = (log: NlqLogEntry, purposes: string[]) =>
    log.llm_calls.filter((call) => purposes.includes(call.purpose));

const NLQSettings: React.FC = () => {
    const navigate = useNavigate();
    const [settings, setSettings] = useState<MLLESettings | null>(null);
    const [repos, setRepos] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [loadingLogs, setLoadingLogs] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [logs, setLogs] = useState<NlqLogEntry[]>([]);

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            setError(null);
            try {
                const [loadedSettings, loadedRepos] = await Promise.all([
                    getSettings(),
                    listSettingsRepos().catch(() => []),
                ]);
                setSettings(loadedSettings);
                setRepos(loadedRepos);
                if (loadedSettings.enable_nlq_logging) {
                    setLoadingLogs(true);
                    try {
                        setLogs(await getNlqLogs(20));
                    } finally {
                        setLoadingLogs(false);
                    }
                }
            } catch (err) {
                setError((err as Error).message);
            } finally {
                setLoading(false);
            }
        };
        void load();
    }, []);

    const updateProviderField = (providerKey: string, field: 'base_url' | 'api_key' | 'model', value: string) => {
        if (!settings) return;
        setSettings({
            ...settings,
            llm_providers: {
                ...settings.llm_providers,
                [providerKey]: {
                    ...settings.llm_providers[providerKey],
                    [field]: value,
                },
            },
        });
    };

    const handleSave = async () => {
        if (!settings) return;
        setSaving(true);
        setMessage(null);
        setError(null);
        try {
            const saved = await saveSettings(settings);
            setSettings(saved);
            setMessage('Settings saved.');
        } catch (err) {
            setError((err as Error).message);
        } finally {
            setSaving(false);
        }
    };

    const handleTest = async () => {
        if (!settings) return;
        setTesting(true);
        setMessage(null);
        setError(null);
        try {
            const response = await testLlmConnection(settings);
            setMessage(`LLM test response: ${response}`);
        } catch (err) {
            setError((err as Error).message);
        } finally {
            setTesting(false);
        }
    };

    const handleRefreshLogs = async () => {
        setLoadingLogs(true);
        setError(null);
        try {
            setLogs(await getNlqLogs(20));
        } catch (err) {
            setError((err as Error).message);
        } finally {
            setLoadingLogs(false);
        }
    };

    if (loading || !settings) {
        return <div className="page-container"><h2>Settings</h2><p>Loading…</p></div>;
    }

    const activeProvider = settings.active_llm_provider;
    const activeConfig = settings.llm_providers[activeProvider];

    return (
        <div className="page-container">
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem'}}>
                <h2>Settings</h2>
                <button type="button" onClick={() => navigate('/')}>
                    Back to Home
                </button>
            </div>

            <p>Global application settings. LLM and GraphDB options configured here are shared across the app.</p>

            <div style={{display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '720px'}}>
                <section style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                    <h3>LLM Provider</h3>
                    <label>
                        Provider
                        <select
                            value={settings.active_llm_provider}
                            onChange={(e) => setSettings({...settings, active_llm_provider: e.target.value})}
                            style={{display: 'block', width: '100%', marginTop: '0.25rem'}}
                        >
                            {providerOptions.map((option) => (
                                <option key={option.value} value={option.value}>{option.label}</option>
                            ))}
                        </select>
                    </label>

                    {activeConfig.provider === 'lm_studio' && (
                        <label>
                            Base URL
                            <input
                                type="text"
                                value={activeConfig.base_url ?? ''}
                                onChange={(e) => updateProviderField(activeProvider, 'base_url', e.target.value)}
                                style={{display: 'block', width: '100%', marginTop: '0.25rem'}}
                            />
                        </label>
                    )}

                    {activeConfig.provider !== 'lm_studio' && (
                        <label>
                            API Key
                            <input
                                type="password"
                                value={activeConfig.api_key ?? ''}
                                onChange={(e) => updateProviderField(activeProvider, 'api_key', e.target.value)}
                                style={{display: 'block', width: '100%', marginTop: '0.25rem'}}
                            />
                        </label>
                    )}

                    <label>
                        Model Name
                        <input
                            type="text"
                            value={activeConfig.model}
                            onChange={(e) => updateProviderField(activeProvider, 'model', e.target.value)}
                            style={{display: 'block', width: '100%', marginTop: '0.25rem'}}
                        />
                    </label>

                    <button type="button" onClick={handleTest} disabled={testing}>
                        {testing ? 'Testing…' : 'Test Connection'}
                    </button>
                </section>

                <section style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                    <h3>GraphDB</h3>
                    <label>
                        GraphDB URL
                        <input
                            type="text"
                            value={settings.graphdb_url}
                            onChange={(e) => setSettings({...settings, graphdb_url: e.target.value})}
                            style={{display: 'block', width: '100%', marginTop: '0.25rem'}}
                        />
                    </label>

                    <label>
                        Default Repository
                        <select
                            value={settings.graphdb_default_repo}
                            onChange={(e) => setSettings({...settings, graphdb_default_repo: e.target.value})}
                            style={{display: 'block', width: '100%', marginTop: '0.25rem'}}
                        >
                            <option value={settings.graphdb_default_repo}>{settings.graphdb_default_repo}</option>
                            {repos.filter((repo) => repo !== settings.graphdb_default_repo).map((repo) => (
                                <option key={repo} value={repo}>{repo}</option>
                            ))}
                        </select>
                    </label>

                    <label>
                        Repo Allowlist
                        <input
                            type="text"
                            value={(settings.graphdb_repo_allowlist ?? []).join(', ')}
                            onChange={(e) => setSettings({
                                ...settings,
                                graphdb_repo_allowlist: e.target.value
                                    .split(',')
                                    .map((item) => item.trim())
                                    .filter(Boolean),
                            })}
                            placeholder="mllo3, mllo_test"
                            style={{display: 'block', width: '100%', marginTop: '0.25rem'}}
                        />
                    </label>
                </section>

                <section style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                    <h3>Answer Mode</h3>
                    <label title="Exact disables inference and favors direct graph matches.">
                        <input
                            type="radio"
                            checked={settings.answer_mode === 'exact'}
                            onChange={() => setSettings({...settings, answer_mode: 'exact'})}
                        /> Exact
                    </label>
                    <label title="Conceptual enables inference for category and hierarchy questions.">
                        <input
                            type="radio"
                            checked={settings.answer_mode === 'conceptual'}
                            onChange={() => setSettings({...settings, answer_mode: 'conceptual'})}
                        /> Conceptual
                    </label>
                    <label title="Auto uses the intent classifier to decide whether inference is needed.">
                        <input
                            type="radio"
                            checked={settings.answer_mode === 'auto'}
                            onChange={() => setSettings({...settings, answer_mode: 'auto'})}
                        /> Auto (recommended)
                    </label>
                </section>

                <section style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                    <h3>NLQ Logging</h3>
                    <label title="When enabled, each NLQ/chat run writes a structured log with intent, prompts, SPARQL, results, and answer output.">
                        <input
                            type="checkbox"
                            checked={settings.enable_nlq_logging}
                            onChange={(e) => setSettings({...settings, enable_nlq_logging: e.target.checked})}
                        /> Enable NLQ / chat logging
                    </label>
                    <div style={{display: 'flex', gap: '0.5rem'}}>
                        <button type="button" onClick={handleRefreshLogs} disabled={loadingLogs || !settings.enable_nlq_logging}>
                            {loadingLogs ? 'Refreshing…' : 'Refresh Logs'}
                        </button>
                    </div>
                    {!settings.enable_nlq_logging && (
                        <p style={{margin: 0, color: '#666'}}>Turn logging on and save settings to start recording new NLQ/chat runs.</p>
                    )}
                    {settings.enable_nlq_logging && (
                        <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                            {logs.length === 0 ? (
                                <p style={{margin: 0, color: '#666'}}>No logs recorded yet.</p>
                            ) : (
                                logs.map((log) => {
                                    const payload = log.payload ?? {};
                                    const response = (payload.response as Record<string, unknown> | undefined) ?? {};
                                    const plan = ((payload.plan as Array<Record<string, unknown>> | undefined) ?? []);
                                    const steps = ((payload.steps as Array<Record<string, unknown>> | undefined) ?? []);
                                    const intent = (response.intent as Record<string, unknown> | undefined) ?? {};
                                    const intentCall = llmCallForPurpose(log, 'intent_classification');
                                    const answerCall = llmCallForPurpose(log, 'answer_generation');
                                    const sparqlCalls = llmCallsForPurposes(log, [
                                        'sparql_generation',
                                        'sparql_repair_validation',
                                        'sparql_repair_execution',
                                    ]);
                                    return (
                                        <details key={log.request_id} style={{border: '1px solid #ddd', borderRadius: '8px', padding: '0.75rem', background: '#fafafa'}}>
                                            <summary style={{cursor: 'pointer'}}>
                                                <strong>{String(log.metadata?.question ?? 'Untitled log')}</strong>
                                                <span style={{marginLeft: '0.5rem', color: log.success ? '#166534' : '#b91c1c'}}>
                                                    {log.success ? 'Success' : 'Failed'}
                                                </span>
                                            </summary>
                                            <div style={{marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                                                <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem'}}>
                                                    <div><strong>Started</strong><div>{new Date(log.started_at).toLocaleString()}</div></div>
                                                    <div><strong>Intent</strong><div>{String(intent.tool ?? 'Unknown')}</div></div>
                                                    <div><strong>Repo</strong><div>{String(response.repo_used ?? log.metadata?.repo_requested ?? '')}</div></div>
                                                    <div><strong>Rows</strong><div>{Array.isArray(response.results) ? response.results.length : 0}</div></div>
                                                </div>

                                                <div style={{borderTop: '1px solid #e5e7eb', paddingTop: '0.75rem'}}>
                                                    <strong>Step 1. Intent classification</strong>
                                                    <div style={{marginTop: '0.4rem'}}><strong>Reasoning:</strong> {String(intent.reasoning ?? 'No reasoning recorded.')}</div>
                                                    {intentCall && (
                                                        <details style={{marginTop: '0.5rem'}}>
                                                            <summary>Show intent prompt and model response</summary>
                                                            <div style={{marginTop: '0.5rem', display: 'grid', gap: '0.5rem'}}>
                                                                <div><strong>Provider:</strong> {intentCall.provider} · <strong>Model:</strong> {intentCall.model}</div>
                                                                <div><strong>Prompt</strong></div>
                                                                <pre style={{margin: 0, whiteSpace: 'pre-wrap', maxHeight: '220px', overflow: 'auto'}}>{prettyJson(intentCall.messages)}</pre>
                                                                <div><strong>Model response</strong></div>
                                                                <pre style={{margin: 0, whiteSpace: 'pre-wrap', maxHeight: '220px', overflow: 'auto'}}>{String(intentCall.response_text ?? intentCall.error ?? '')}</pre>
                                                            </div>
                                                        </details>
                                                    )}
                                                </div>

                                                {steps.map((step, index) => {
                                                    const matchingPlan = plan[index];
                                                    const stepTool = String(step.tool ?? matchingPlan?.tool ?? 'unknown_step');
                                                    const stepResults = Array.isArray(step.results) ? step.results : [];
                                                    return (
                                                        <div key={`${log.request_id}-step-${index}`} style={{borderTop: '1px solid #e5e7eb', paddingTop: '0.75rem'}}>
                                                            <strong>Step {index + 2}. {stepTool}</strong>
                                                            {Boolean(matchingPlan?.reasoning) && (
                                                                <div style={{marginTop: '0.4rem'}}><strong>Planned because:</strong> {String(matchingPlan.reasoning)}</div>
                                                            )}
                                                            {Boolean(step.reasoning) && (
                                                                <div style={{marginTop: '0.25rem'}}><strong>Execution note:</strong> {String(step.reasoning)}</div>
                                                            )}
                                                            <div style={{marginTop: '0.25rem'}}><strong>Result count:</strong> {stepResults.length}</div>
                                                            <details style={{marginTop: '0.5rem'}}>
                                                                <summary>Show step details</summary>
                                                                <div style={{marginTop: '0.5rem', display: 'grid', gap: '0.5rem'}}>
                                                                    <div><strong>Params</strong></div>
                                                                    <pre style={{margin: 0, whiteSpace: 'pre-wrap', maxHeight: '180px', overflow: 'auto'}}>{prettyJson(step.params ?? {})}</pre>
                                                                    <div><strong>SPARQL / chain fragment</strong></div>
                                                                    <pre style={{margin: 0, whiteSpace: 'pre-wrap', maxHeight: '220px', overflow: 'auto'}}>{String(step.sparql ?? '')}</pre>
                                                                    <div><strong>Result preview</strong></div>
                                                                    <pre style={{margin: 0, whiteSpace: 'pre-wrap', maxHeight: '220px', overflow: 'auto'}}>{prettyJson(stepResults.slice(0, 10))}</pre>
                                                                </div>
                                                            </details>
                                                        </div>
                                                    );
                                                })}

                                                {sparqlCalls.length > 0 && (
                                                    <div style={{borderTop: '1px solid #e5e7eb', paddingTop: '0.75rem'}}>
                                                        <strong>Query generation details</strong>
                                                        <div style={{marginTop: '0.4rem', color: '#666'}}>These are the LLM calls used to build or repair custom SPARQL.</div>
                                                        <div style={{display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem'}}>
                                                            {sparqlCalls.map((call, index) => (
                                                                <details key={`${log.request_id}-llm-${index}`}>
                                                                    <summary>{call.purpose}</summary>
                                                                    <div style={{marginTop: '0.5rem', display: 'grid', gap: '0.5rem'}}>
                                                                        <div><strong>Provider:</strong> {call.provider} · <strong>Model:</strong> {call.model}</div>
                                                                        <div><strong>Prompt</strong></div>
                                                                        <pre style={{margin: 0, whiteSpace: 'pre-wrap', maxHeight: '220px', overflow: 'auto'}}>{prettyJson(call.messages)}</pre>
                                                                        <div><strong>Model response</strong></div>
                                                                        <pre style={{margin: 0, whiteSpace: 'pre-wrap', maxHeight: '220px', overflow: 'auto'}}>{String(call.response_text ?? call.error ?? '')}</pre>
                                                                    </div>
                                                                </details>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                <div style={{borderTop: '1px solid #e5e7eb', paddingTop: '0.75rem'}}>
                                                    <strong>Final step. Answer generation</strong>
                                                    <div style={{marginTop: '0.4rem'}}><strong>Answer</strong></div>
                                                    <pre style={{margin: 0, whiteSpace: 'pre-wrap'}}>{String(response.answer ?? '')}</pre>
                                                    {answerCall && (
                                                        <details style={{marginTop: '0.5rem'}}>
                                                            <summary>Show answer prompt and model response</summary>
                                                            <div style={{marginTop: '0.5rem', display: 'grid', gap: '0.5rem'}}>
                                                                <div><strong>Provider:</strong> {answerCall.provider} · <strong>Model:</strong> {answerCall.model}</div>
                                                                <div><strong>Prompt</strong></div>
                                                                <pre style={{margin: 0, whiteSpace: 'pre-wrap', maxHeight: '220px', overflow: 'auto'}}>{prettyJson(answerCall.messages)}</pre>
                                                                <div><strong>Model response</strong></div>
                                                                <pre style={{margin: 0, whiteSpace: 'pre-wrap', maxHeight: '220px', overflow: 'auto'}}>{String(answerCall.response_text ?? answerCall.error ?? '')}</pre>
                                                            </div>
                                                        </details>
                                                    )}
                                                </div>

                                                {log.error && (
                                                    <>
                                                        <div style={{borderTop: '1px solid #e5e7eb', paddingTop: '0.75rem'}}><strong>Error</strong></div>
                                                        <pre style={{margin: 0, whiteSpace: 'pre-wrap'}}>{log.error}</pre>
                                                    </>
                                                )}
                                            </div>
                                        </details>
                                    );
                                })
                            )}
                        </div>
                    )}
                </section>

                <div style={{display: 'flex', gap: '0.5rem'}}>
                    <button type="button" onClick={handleSave} disabled={saving}>
                        {saving ? 'Saving…' : 'Save'}
                    </button>
                </div>

                {message && <div style={{color: 'green'}}>{message}</div>}
                {error && <div style={{color: 'red'}}>{error}</div>}
            </div>
        </div>
    );
};

export default NLQSettings;
