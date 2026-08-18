import React, {useEffect, useState} from 'react';
import {NavLink, Navigate, Outlet, useNavigate, useOutletContext} from 'react-router-dom';
import {
    CodexHistoryEntry,
    getCodexHistory,
    getNlqLogs,
    getSettings,
    listSettingsRepos,
    MLLESettings,
    NlqLogEntry,
    testLlmConnection
} from '../../services/api';
import './styles/plot_performance.css';
import './styles/settings.css';

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
            {label: 'Codex History', path: '/settings/codex-history', description: 'Local Codex chat transcripts for this project'},
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
    repos: string[];
    logs: NlqLogEntry[];
    codexHistory: CodexHistoryEntry[];
    loadingLogs: boolean;
    loadingCodexHistory: boolean;
    testing: boolean;
    message: string | null;
    error: string | null;
    handleTest: () => Promise<void>;
    handleRefreshLogs: () => Promise<void>;
    handleRefreshCodexHistory: (query?: string) => Promise<void>;
};

const useSettingsContext = () => useOutletContext<SettingsContextValue>();

const SettingsOverview: React.FC = () => (
    <Navigate to="/settings/llm" replace />
);

export const SettingsLlmPage: React.FC = () => {
    const {settings, testing, handleTest} = useSettingsContext();

    return (
        <section className="settings-panel">
            <div className="settings-panel-header">
                <div>
                    <span className="settings-panel-kicker">.env Configuration</span>
                    <h3>LLM Settings</h3>
                    <p>Runtime values are read from the repository .env. Secrets are never returned to this page.</p>
                </div>
                <button type="button" onClick={() => void handleTest()} disabled={testing}>
                    {testing ? 'Testing...' : 'Test Connection'}
                </button>
            </div>

            <div className="settings-form-grid">
                <label className="settings-field settings-field-full">
                    <span>Client Type</span>
                    <input type="text" value={settings.llm_client_type} readOnly />
                </label>

                <label className="settings-field settings-field-full">
                    <span>Base URL</span>
                    <input type="text" value={settings.llm_base_url} readOnly />
                </label>

                {settings.llm_chat_completions_url && (
                    <label className="settings-field settings-field-full">
                        <span>Full Chat Completions URL</span>
                        <input type="text" value={settings.llm_chat_completions_url} readOnly />
                    </label>
                )}

                <label className="settings-field settings-field-full">
                    <span>Model</span>
                    <input type="text" value={settings.llm_model} readOnly />
                    <small>Edit LLM_* values in .env and restart the backend to apply changes.</small>
                </label>
            </div>
        </section>
    );
};

export const SettingsGraphDbPage: React.FC = () => {
    const {settings, repos} = useSettingsContext();

    return (
        <section className="settings-panel">
            <div className="settings-panel-header">
                <div>
                    <span className="settings-panel-kicker">Data Access</span>
                    <h3>GraphDB Settings</h3>
                    <p>GraphDB values are read-only here and come exclusively from the repository .env.</p>
                </div>
            </div>

            <div className="settings-form-grid">
                <label className="settings-field settings-field-full">
                    <span>GraphDB URL</span>
                    <input
                        type="text"
                        value={settings.graphdb_url}
                        readOnly
                    />
                </label>

                <label className="settings-field">
                    <span>Default Repository</span>
                    <input type="text" value={settings.graphdb_default_repo} readOnly />
                    <small>Available repositories: {repos.join(', ') || 'none returned'}</small>
                </label>

                <label className="settings-field settings-field-full">
                    <span>Repo Allowlist</span>
                    <input
                        type="text"
                        value={(settings.graphdb_repo_allowlist ?? []).join(', ')}
                        readOnly
                        placeholder="All repositories"
                    />
                    <small>Edit GRAPHDB_* values in .env and restart the backend to apply changes.</small>
                </label>
            </div>
        </section>
    );
};

export const SettingsLogsPage: React.FC = () => {
    const {settings, logs, loadingLogs, handleRefreshLogs} = useSettingsContext();

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
                        readOnly
                    />
                    <div>
                        <strong>Enable NLQ / chat logging</strong>
                        <p>Set ENABLE_NLQ_LOGGING in .env and restart the backend to change this.</p>
                    </div>
                </label>
            </div>

            {!settings.enable_nlq_logging && (
                <p className="settings-inline-note">Logging is off. Set ENABLE_NLQ_LOGGING=true in .env and restart the backend.</p>
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

export const SettingsCodexHistoryPage: React.FC = () => {
    const {codexHistory, loadingCodexHistory, handleRefreshCodexHistory} = useSettingsContext();
    const [query, setQuery] = useState('');

    return (
        <section className="settings-panel">
            <div className="settings-panel-header">
                <div>
                    <span className="settings-panel-kicker">Local Archive</span>
                    <h3>Codex Chat History</h3>
                    <p>Browse read-only Codex Desktop transcripts tied to this workspace, including archived sessions.</p>
                </div>
                <button type="button" onClick={() => void handleRefreshCodexHistory(query)} disabled={loadingCodexHistory}>
                    {loadingCodexHistory ? 'Refreshing...' : 'Refresh'}
                </button>
            </div>

            <form
                className="settings-history-search"
                onSubmit={(event) => {
                    event.preventDefault();
                    void handleRefreshCodexHistory(query);
                }}
            >
                <label className="settings-field settings-field-full">
                    <span>Search History</span>
                    <input
                        type="search"
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        placeholder="Thread name, question, branch, model, dataset..."
                    />
                </label>
                <button type="submit" disabled={loadingCodexHistory}>
                    Search
                </button>
            </form>

            <div className="settings-log-list">
                {codexHistory.length === 0 ? (
                    <p className="settings-inline-note">No Codex history found for this workspace.</p>
                ) : (
                    codexHistory.map((entry) => (
                        <details key={entry.id} className="settings-log-card">
                            <summary className="settings-log-summary">
                                <strong>{entry.thread_name}</strong>
                                <span>{entry.message_count} messages</span>
                            </summary>
                            <div className="settings-log-content">
                                <div className="settings-log-grid">
                                    <div><strong>Updated</strong><div>{entry.updated_at ? new Date(entry.updated_at).toLocaleString() : 'Unknown'}</div></div>
                                    <div><strong>User Turns</strong><div>{entry.user_message_count}</div></div>
                                    <div><strong>Assistant Turns</strong><div>{entry.assistant_message_count}</div></div>
                                    <div><strong>Session ID</strong><div>{entry.id}</div></div>
                                </div>

                                <div className="settings-log-section">
                                    <strong>Workspace</strong>
                                    <pre>{entry.cwd || 'Unknown workspace'}</pre>
                                </div>

                                <div className="settings-log-section">
                                    <strong>First user message</strong>
                                    <pre>{entry.first_user_message || 'No user message captured.'}</pre>
                                </div>

                                <div className="settings-log-section">
                                    <strong>Recent conversation</strong>
                                    <div className="settings-history-message-list">
                                        {entry.recent_messages.map((message, index) => (
                                            <div key={`${entry.id}-${index}`} className={`settings-history-message is-${message.role}`}>
                                                <strong>{message.role === 'user' ? 'User' : 'Codex'}</strong>
                                                <pre>{message.text}</pre>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="settings-log-section">
                                    <strong>Source file</strong>
                                    <pre>{entry.source_path}</pre>
                                </div>
                            </div>
                        </details>
                    ))
                )}
            </div>
        </section>
    );
};

const NLQSettings: React.FC = () => {
    const navigate = useNavigate();
    const [settings, setSettings] = useState<MLLESettings | null>(null);
    const [repos, setRepos] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [testing, setTesting] = useState(false);
    const [loadingLogs, setLoadingLogs] = useState(false);
    const [loadingCodexHistory, setLoadingCodexHistory] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [logs, setLogs] = useState<NlqLogEntry[]>([]);
    const [codexHistory, setCodexHistory] = useState<CodexHistoryEntry[]>([]);

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
                setLoadingCodexHistory(true);
                try {
                    setCodexHistory(await getCodexHistory(50));
                } finally {
                    setLoadingCodexHistory(false);
                }
            } catch (err) {
                setError((err as Error).message);
            } finally {
                setLoading(false);
            }
        };

        void load();
    }, []);

    const handleTest = async () => {
        if (!settings) return;
        setTesting(true);
        setMessage(null);
        setError(null);
        try {
            const response = await testLlmConnection();
            setMessage(`LLM test response: ${response}`);
        } catch (err) {
            setError((err as Error).message);
        } finally {
            setTesting(false);
        }
    };

    const handleRefreshCodexHistory = async (query = '') => {
        setLoadingCodexHistory(true);
        setError(null);
        try {
            setCodexHistory(await getCodexHistory(50, query));
        } catch (err) {
            setError((err as Error).message);
        } finally {
            setLoadingCodexHistory(false);
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
                    <p>Read-only runtime configuration loaded from the repository .env. Restart the backend after editing it.</p>
                </div>
                <div className="settings-hero-actions">
                    <button type="button" onClick={() => navigate('/')}>
                        Back to Home
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
                            repos,
                            logs,
                            codexHistory,
                            loadingLogs,
                            loadingCodexHistory,
                            testing,
                            message,
                            error,
                            handleTest,
                            handleRefreshLogs,
                            handleRefreshCodexHistory,
                        }}
                    />
                </main>
            </div>
        </div>
    );
};

export default NLQSettings;
export {SettingsOverview};
