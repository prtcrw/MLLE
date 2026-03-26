import React, {useEffect, useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {
    getSettings,
    listSettingsRepos,
    MLLESettings,
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

const NLQSettings: React.FC = () => {
    const navigate = useNavigate();
    const [settings, setSettings] = useState<MLLESettings | null>(null);
    const [repos, setRepos] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

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
