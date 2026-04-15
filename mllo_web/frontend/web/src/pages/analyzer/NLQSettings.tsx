import React, {useEffect, useState} from 'react';
import {NavLink, Navigate, Outlet, useNavigate, useOutletContext} from 'react-router-dom';
import {
    getNlqLogs,
    getSettings,
    listSettingsRepos,
    MLLESettings,
    NlqLogEntry,
    saveSettings,
    testLlmConnection
} from '../../services/api';
import './styles/plot_performance.css';
import './styles/settings.css';

const providerOptions = [
    {value: 'lm_studio', label: 'LM Studio'},
    {value: 'ollama', label: 'Ollama'},
    {value: 'openai', label: 'OpenAI'},
    {value: 'azure_openai', label: 'Azure OpenAI'},
    {value: 'anthropic', label: 'Anthropic'},
    {value: 'gemini', label: 'Gemini'},
];

const settingsSections = [
    {
        title: 'Workspace',
        items: [
            {label: 'LLM', path: '/settings/llm', description: 'Providers, models, and connection testing'},
            {label: 'GraphDB', path: '/settings/graphdb', description: 'Endpoint, repositories, and access scope'},
        ],
    },
    {
        title: 'Diagnostics',
        items: [
            {label: 'Logs', path: '/settings/logs', description: 'NLQ trace logging and recent runs'},
        ],
    },
];

const prettyJson = (value: unknown) => JSON.stringify(value, null, 2);

const llmCallForPurpose = (log: NlqLogEntry, purpose: string) =>
    log.llm_calls.find((call) => call.purpose === purpose);

const llmCallsForPurposes = (log: NlqLogEntry, purposes: string[]) =>
    log.llm_calls.filter((call) => purposes.includes(call.purpose));

type SettingsContextValue = {
    settings: MLLESettings;
    setSettings: React.Dispatch<React.SetStateAction<MLLESettings | null>>;
    repos: string[];
    logs: NlqLogEntry[];
    loadingLogs: boolean;
    saving: boolean;
    testing: boolean;
    message: string | null;
    error: string | null;
    handleSave: () => Promise<void>;
    handleTest: () => Promise<void>;
    handleRefreshLogs: () => Promise<void>;
    updateProviderField: (
        providerKey: string,
        field: 'base_url' | 'api_key' | 'api_version' | 'model',
        value: string,
    ) => void;
};

const useSettingsContext = () => useOutletContext<SettingsContextValue>();

const SettingsOverview: React.FC = () => (
    <Navigate to="/settings/llm" replace />
);

export const SettingsLlmPage: React.FC = () => {
    const {settings, setSettings, testing, handleTest, updateProviderField} = useSettingsContext();
    const activeProvider = settings.active_llm_provider;
    const activeConfig = settings.llm_providers[activeProvider];

    return (
        <section className="settings-panel">
            <div className="settings-panel-header">
                <div>
                    <span className="settings-panel-kicker">Provider Setup</span>
                    <h3>LLM Settings</h3>
                    <p>Choose the active provider, set credentials, and verify the current model can answer requests.</p>
                </div>
                <button type="button" onClick={() => void handleTest()} disabled={testing}>
                    {testing ? 'Testing...' : 'Test Connection'}
                </button>
            </div>

            <div className="settings-form-grid">
                <label className="settings-field settings-field-full">
                    <span>Provider</span>
                    <select
                        value={settings.active_llm_provider}
                        onChange={(e) => setSettings((current) => current ? {...current, active_llm_provider: e.target.value} : current)}
                    >
                        {providerOptions.map((option) => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                    </select>
                </label>

                {(activeConfig.provider === 'lm_studio' || activeConfig.provider === 'ollama') && (
                    <label className="settings-field settings-field-full">
                        <span>Base URL</span>
                        <input
                            type="text"
                            value={activeConfig.base_url ?? ''}
                            onChange={(e) => updateProviderField(activeProvider, 'base_url', e.target.value)}
                            placeholder={activeConfig.provider === 'ollama' ? 'http://localhost:11434/v1' : 'http://localhost:1234/v1'}
                        />
                    </label>
                )}

                {activeConfig.provider === 'azure_openai' && (
                    <>
                        <label className="settings-field settings-field-full">
                            <span>Azure Endpoint</span>
                            <input
                                type="text"
                                value={activeConfig.base_url ?? ''}
                                onChange={(e) => updateProviderField(activeProvider, 'base_url', e.target.value)}
                                placeholder="https://YOUR-RESOURCE.openai.azure.com"
                            />
                        </label>
                        <label className="settings-field">
                            <span>API Version</span>
                            <input
                                type="text"
                                value={activeConfig.api_version ?? ''}
                                onChange={(e) => updateProviderField(activeProvider, 'api_version', e.target.value)}
                                placeholder="2024-10-21"
                            />
                        </label>
                    </>
                )}

                {activeConfig.provider !== 'lm_studio' && activeConfig.provider !== 'ollama' && (
                    <label className="settings-field settings-field-full">
                        <span>API Key</span>
                        <input
                            type="password"
                            value={activeConfig.api_key ?? ''}
                            onChange={(e) => updateProviderField(activeProvider, 'api_key', e.target.value)}
                            placeholder="Enter API key"
                        />
                    </label>
                )}

                <label className="settings-field settings-field-full">
                    <span>{activeConfig.provider === 'azure_openai' ? 'Deployment Name' : 'Model Name'}</span>
                    <input
                        type="text"
                        value={activeConfig.model}
                        onChange={(e) => updateProviderField(activeProvider, 'model', e.target.value)}
                        placeholder={
                            activeConfig.provider === 'azure_openai'
                                ? 'your-deployment-name'
                                : activeConfig.provider === 'ollama'
                                    ? 'llama3.1'
                                    : 'gpt-4.1-mini'
                        }
                    />
                </label>
            </div>
        </section>
    );
};

export const SettingsGraphDbPage: React.FC = () => {
    const {settings, setSettings, repos} = useSettingsContext();

    return (
        <section className="settings-panel">
            <div className="settings-panel-header">
                <div>
                    <span className="settings-panel-kicker">Data Access</span>
                    <h3>GraphDB Settings</h3>
                    <p>Control the knowledge graph endpoint, pick the default repository, and optionally limit the repo list.</p>
                </div>
            </div>

            <div className="settings-form-grid">
                <label className="settings-field settings-field-full">
                    <span>GraphDB URL</span>
                    <input
                        type="text"
                        value={settings.graphdb_url}
                        onChange={(e) => setSettings((current) => current ? {...current, graphdb_url: e.target.value} : current)}
                    />
                </label>

                <label className="settings-field">
                    <span>Default Repository</span>
                    <select
                        value={settings.graphdb_default_repo}
                        onChange={(e) => setSettings((current) => current ? {...current, graphdb_default_repo: e.target.value} : current)}
                    >
                        <option value={settings.graphdb_default_repo}>{settings.graphdb_default_repo}</option>
                        {repos.filter((repo) => repo !== settings.graphdb_default_repo).map((repo) => (
                            <option key={repo} value={repo}>{repo}</option>
                        ))}
                    </select>
                </label>

                <label className="settings-field settings-field-full">
                    <span>Repo Allowlist</span>
                    <input
                        type="text"
                        value={(settings.graphdb_repo_allowlist ?? []).join(', ')}
                        onChange={(e) => setSettings((current) => current ? {
                            ...current,
                            graphdb_repo_allowlist: e.target.value
                                .split(',')
                                .map((item) => item.trim())
                                .filter(Boolean),
                        } : current)}
                        placeholder="mllo3, mllo_test"
                    />
                    <small>Leave blank to allow every repository the backend returns.</small>
                </label>
            </div>
        </section>
    );
};

export const SettingsLogsPage: React.FC = () => {
    const {settings, setSettings, logs, loadingLogs, handleRefreshLogs} = useSettingsContext();

    return (
        <section className="settings-panel">
            <div className="settings-panel-header">
                <div>
                    <span className="settings-panel-kicker">Diagnostics</span>
                    <h3>NLQ Logging</h3>
                    <p>Capture recent NLQ and chat runs, including prompts, tool calls, generated SPARQL, and final answers.</p>
                </div>
                <button type="button" onClick={() => void handleRefreshLogs()} disabled={loadingLogs || !settings.enable_nlq_logging}>
                    {loadingLogs ? 'Refreshing...' : 'Refresh Logs'}
                </button>
            </div>

            <div className="settings-choice-list">
                <label className="settings-choice-card" title="When enabled, each NLQ/chat run writes a structured log with intent, prompts, SPARQL, results, and answer output.">
                    <input
                        type="checkbox"
                        checked={settings.enable_nlq_logging}
                        onChange={(e) => setSettings((current) => current ? {...current, enable_nlq_logging: e.target.checked} : current)}
                    />
                    <div>
                        <strong>Enable NLQ / chat logging</strong>
                        <p>Turn this on and save to start recording new runs for debugging and analysis.</p>
                    </div>
                </label>
            </div>

            {!settings.enable_nlq_logging && (
                <p className="settings-inline-note">Logging is off right now. Save after enabling it to start collecting new entries.</p>
            )}

            {settings.enable_nlq_logging && (
                <div className="settings-log-list">
                    {logs.length === 0 ? (
                        <p className="settings-inline-note">No logs recorded yet.</p>
                    ) : (
                        logs.map((log) => {
                            const payload = log.payload ?? {};
                            const response = (payload.response as Record<string, unknown> | undefined) ?? {};
                            const plan = ((payload.plan as Array<Record<string, unknown>> | undefined) ?? []);
                            const steps = ((payload.steps as Array<Record<string, unknown>> | undefined) ?? []);
                            const intent = (response.intent as Record<string, unknown> | undefined) ?? {};
                            const intentCall = llmCallForPurpose(log, 'intent_classification');
                            const answerCall = llmCallForPurpose(log, 'answer_generation');
                            const primaryModel =
                                answerCall?.model ??
                                intentCall?.model ??
                                log.llm_calls.find((call) => Boolean(call.model))?.model ??
                                'Unknown';
                            const sparqlCalls = llmCallsForPurposes(log, [
                                'sparql_generation',
                                'sparql_repair_validation',
                                'sparql_repair_execution',
                            ]);

                            return (
                                <details key={log.request_id} className="settings-log-card">
                                    <summary className="settings-log-summary">
                                        <strong>{String(log.metadata?.question ?? 'Untitled log')}</strong>
                                        <span className={log.success ? 'is-success' : 'is-failure'}>
                                            {log.success ? 'Success' : 'Failed'}
                                        </span>
                                    </summary>
                                    <div className="settings-log-content">
                                        <div className="settings-log-grid">
                                            <div><strong>Started</strong><div>{new Date(log.started_at).toLocaleString()}</div></div>
                                            <div><strong>LLM Model</strong><div>{String(primaryModel)}</div></div>
                                            <div><strong>Intent</strong><div>{String(intent.tool ?? 'Unknown')}</div></div>
                                            <div><strong>Repo</strong><div>{String(response.repo_used ?? log.metadata?.repo_requested ?? '')}</div></div>
                                            <div><strong>Rows</strong><div>{Array.isArray(response.results) ? response.results.length : 0}</div></div>
                                        </div>

                                        <div className="settings-log-section">
                                            <strong>Step 1. Intent classification</strong>
                                            <div><strong>Reasoning:</strong> {String(intent.reasoning ?? 'No reasoning recorded.')}</div>
                                            {intentCall && (
                                                <details>
                                                    <summary>Show intent prompt and model response</summary>
                                                    <div className="settings-log-detail-grid">
                                                        <div><strong>Provider:</strong> {intentCall.provider} · <strong>Model:</strong> {intentCall.model}</div>
                                                        <div><strong>Prompt</strong></div>
                                                        <pre>{prettyJson(intentCall.messages)}</pre>
                                                        <div><strong>Model response</strong></div>
                                                        <pre>{String(intentCall.response_text ?? intentCall.error ?? '')}</pre>
                                                    </div>
                                                </details>
                                            )}
                                        </div>

                                        {steps.map((step, index) => {
                                            const matchingPlan = plan[index];
                                            const stepTool = String(step.tool ?? matchingPlan?.tool ?? 'unknown_step');
                                            const stepResults = Array.isArray(step.results) ? step.results : [];

                                            return (
                                                <div key={`${log.request_id}-step-${index}`} className="settings-log-section">
                                                    <strong>Step {index + 2}. {stepTool}</strong>
                                                    {Boolean(matchingPlan?.reasoning) && (
                                                        <div><strong>Planned because:</strong> {String(matchingPlan.reasoning)}</div>
                                                    )}
                                                    {Boolean(step.reasoning) && (
                                                        <div><strong>Execution note:</strong> {String(step.reasoning)}</div>
                                                    )}
                                                    <div><strong>Result count:</strong> {stepResults.length}</div>
                                                    <details>
                                                        <summary>Show step details</summary>
                                                        <div className="settings-log-detail-grid">
                                                            <div><strong>Params</strong></div>
                                                            <pre>{prettyJson(step.params ?? {})}</pre>
                                                            <div><strong>SPARQL / chain fragment</strong></div>
                                                            <pre>{String(step.sparql ?? '')}</pre>
                                                            <div><strong>Result preview</strong></div>
                                                            <pre>{prettyJson(stepResults.slice(0, 10))}</pre>
                                                        </div>
                                                    </details>
                                                </div>
                                            );
                                        })}

                                        {sparqlCalls.length > 0 && (
                                            <div className="settings-log-section">
                                                <strong>Query generation details</strong>
                                                <div className="settings-muted-copy">These are the LLM calls used to build or repair custom SPARQL.</div>
                                                <div className="settings-log-stack">
                                                    {sparqlCalls.map((call, index) => (
                                                        <details key={`${log.request_id}-llm-${index}`}>
                                                            <summary>{call.purpose}</summary>
                                                            <div className="settings-log-detail-grid">
                                                                <div><strong>Provider:</strong> {call.provider} · <strong>Model:</strong> {call.model}</div>
                                                                <div><strong>Prompt</strong></div>
                                                                <pre>{prettyJson(call.messages)}</pre>
                                                                <div><strong>Model response</strong></div>
                                                                <pre>{String(call.response_text ?? call.error ?? '')}</pre>
                                                            </div>
                                                        </details>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        <div className="settings-log-section">
                                            <strong>Final step. Answer generation</strong>
                                            <div><strong>Answer</strong></div>
                                            <pre>{String(response.answer ?? '')}</pre>
                                            {answerCall && (
                                                <details>
                                                    <summary>Show answer prompt and model response</summary>
                                                    <div className="settings-log-detail-grid">
                                                        <div><strong>Provider:</strong> {answerCall.provider} · <strong>Model:</strong> {answerCall.model}</div>
                                                        <div><strong>Prompt</strong></div>
                                                        <pre>{prettyJson(answerCall.messages)}</pre>
                                                        <div><strong>Model response</strong></div>
                                                        <pre>{String(answerCall.response_text ?? answerCall.error ?? '')}</pre>
                                                    </div>
                                                </details>
                                            )}
                                        </div>

                                        {log.error && (
                                            <div className="settings-log-section">
                                                <strong>Error</strong>
                                                <pre>{log.error}</pre>
                                            </div>
                                        )}
                                    </div>
                                </details>
                            );
                        })
                    )}
                </div>
            )}
        </section>
    );
};

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

    const updateProviderField = (
        providerKey: string,
        field: 'base_url' | 'api_key' | 'api_version' | 'model',
        value: string,
    ) => {
        setSettings((current) => {
            if (!current) return current;
            return {
                ...current,
                llm_providers: {
                    ...current.llm_providers,
                    [providerKey]: {
                        ...current.llm_providers[providerKey],
                        [field]: value,
                    },
                },
            };
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
        return <div className="page-container"><h2>Settings</h2><p>Loading...</p></div>;
    }

    return (
        <div className="page-container settings-page">
            <section className="settings-hero">
                <div>
                    <span className="plot-performance-kicker">Settings</span>
                    <h1>Application Settings</h1>
                    <p>Organized into focused pages so you can move through setup the way you would in a code editor.</p>
                </div>
                <div className="settings-hero-actions">
                    <button type="button" onClick={() => navigate('/')}>
                        Back to Home
                    </button>
                    <button type="button" onClick={() => void handleSave()} disabled={saving}>
                        {saving ? 'Saving...' : 'Save'}
                    </button>
                </div>
            </section>

            {(message || error) && (
                <div className={`settings-feedback ${error ? 'is-error' : 'is-success'}`}>
                    {error ?? message}
                </div>
            )}

            <div className="settings-shell">
                <aside className="settings-sidebar" aria-label="Settings categories">
                    {settingsSections.map((section) => (
                        <section key={section.title} className="settings-sidebar-group">
                            <h2>{section.title}</h2>
                            <nav className="settings-sidebar-nav">
                                {section.items.map((item) => (
                                    <NavLink
                                        key={item.path}
                                        to={item.path}
                                        end
                                        className={({isActive}) => `settings-sidebar-link${isActive ? ' is-active' : ''}`}
                                    >
                                        <strong>{item.label}</strong>
                                        <span>{item.description}</span>
                                    </NavLink>
                                ))}
                            </nav>
                        </section>
                    ))}
                </aside>

                <main className="settings-main">
                    <Outlet
                        context={{
                            settings,
                            setSettings,
                            repos,
                            logs,
                            loadingLogs,
                            saving,
                            testing,
                            message,
                            error,
                            handleSave,
                            handleTest,
                            handleRefreshLogs,
                            updateProviderField,
                        }}
                    />
                </main>
            </div>
        </div>
    );
};

export default NLQSettings;
export {SettingsOverview};
