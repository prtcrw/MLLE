export const buildV1Url = (path: string): string => `http://localhost:5252/api/v1/${path}`;

export const downloadFromResponse = async (response: Response, default_filename: string) => {
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition');
    let filename = default_filename;

    if (disposition && disposition.startsWith('attachment')) {
        const filenameMatch = disposition.match(/filename\*?=(['"]*)(.*?)\1/i);
        if (filenameMatch && filenameMatch.length > 2) {
            filename = decodeURIComponent(filenameMatch[2]); // Decode filename
        }
    }

    const elm = document.createElement('a');
    elm.href = URL.createObjectURL(blob);
    elm.setAttribute('download', filename);
    elm.click();
    elm.remove();
}

export interface ConvertResult {
    sparql: string;
    results: Record<string, string | null>[];
    error: string | null;
}

export interface LLMProviderConfig {
    provider: 'lm_studio' | 'openai' | 'anthropic' | 'gemini';
    base_url?: string | null;
    api_key?: string | null;
    model: string;
}

export interface MLLESettings {
    active_llm_provider: string;
    llm_providers: Record<string, LLMProviderConfig>;
    graphdb_url: string;
    graphdb_default_repo: string;
    graphdb_repo_allowlist?: string[] | null;
    answer_mode: 'exact' | 'conceptual' | 'auto';
}

export interface QueryIntent {
    tool: string;
    params: Record<string, unknown>;
    use_inference: boolean;
    reasoning: string;
}

export interface NLQResponse {
    question: string;
    intent: QueryIntent;
    sparql: string;
    results: Record<string, string | null>[];
    answer: string;
    repo_used: string;
    inference_used: boolean;
}

export const convertEnglishToSparql = async (input: string, endpoint?: string): Promise<ConvertResult> => {
    // Default to backend dev server where FastAPI serves the convert endpoint
    const base = endpoint ?? (import.meta.env.VITE_LM_ENDPOINT as string) ?? 'http://localhost:5252/api/convert-sparql';
    const resp = await fetch(base, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ input })
    });

    if (!resp.ok) {
        let message = 'Conversion failed.';
        try {
            const payload = await resp.json();
            if (typeof payload?.detail === 'string' && payload.detail.trim().length > 0) {
                message = payload.detail;
            }
        } catch {
            const text = await resp.text();
            if (text.trim().length > 0) {
                message = text;
            }
        }
        throw new Error(message);
    }

    const j = await resp.json();
    return {
        sparql: j.sparql ?? '',
        results: j.results ?? [],
        error: j.error ?? null,
    };
}

export const getSettings = async (): Promise<MLLESettings> => {
    const response = await fetch(buildV1Url('settings'));
    if (!response.ok) {
        throw new Error('Failed to load settings.');
    }
    return await response.json();
}

export const saveSettings = async (settings: MLLESettings): Promise<MLLESettings> => {
    const response = await fetch(buildV1Url('settings'), {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to save settings.');
    }
    return await response.json();
}

export const listSettingsRepos = async (): Promise<string[]> => {
    const response = await fetch(buildV1Url('settings/repos'));
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to load repositories.');
    }
    const payload = await response.json();
    return payload?.repos ?? [];
}

export const testLlmConnection = async (settings?: MLLESettings): Promise<string> => {
    const response = await fetch(buildV1Url('settings/test-llm'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings ?? null),
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'LLM connection test failed.');
    }
    const payload = await response.json();
    return payload?.response ?? 'OK';
}

export const queryNaturalLanguage = async (
    question: string,
    repo?: string,
    answerMode?: 'exact' | 'conceptual' | 'auto',
): Promise<NLQResponse> => {
    const response = await fetch(buildV1Url('nlq/query'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            question,
            repo: repo || undefined,
            answer_mode: answerMode || undefined,
        }),
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Natural language query failed.');
    }
    return await response.json();
}
