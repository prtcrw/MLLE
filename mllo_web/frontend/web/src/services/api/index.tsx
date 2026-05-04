const getApiBaseUrl = (): string => {
    const configuredBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
    if (configuredBase) {
        return configuredBase.replace(/\/$/, '');
    }

    const host = window.location.hostname || '127.0.0.1';
    return `http://${host}:5252/api/v1`;
};

export const buildV1Url = (path: string): string => `${getApiBaseUrl()}/${path}`;

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
    provider: 'lm_studio' | 'ollama' | 'openai' | 'azure_openai' | 'anthropic' | 'gemini';
    base_url?: string | null;
    api_key?: string | null;
    api_version?: string | null;
    model: string;
}

export interface MLLESettings {
    active_llm_provider: string;
    llm_providers: Record<string, LLMProviderConfig>;
    graphdb_url: string;
    graphdb_default_repo: string;
    graphdb_repo_allowlist?: string[] | null;
    answer_mode: 'exact' | 'conceptual' | 'auto';
    enable_nlq_logging: boolean;
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
    results: Record<string, string | null | string[]>[];
    answer: string;
    repo_used: string;
    inference_used: boolean;
}

export interface PipelineEditorNode {
    id: string;
    iri: string;
    title: string;
    kind: 'input' | 'operation' | 'output' | 'model';
    position: number;
    note: string;
    x?: number;
    y?: number;
}

export interface PipelineEditorEdge {
    source: string;
    target: string;
    relation: string;
}

export interface PipelineEditorDraft {
    pipelineName: string;
    savedAt: string;
    validationStatus: 'unknown' | 'passed' | 'failed';
    validationMessage: string;
    nodes: PipelineEditorNode[];
    edges: PipelineEditorEdge[];
}

export interface PipelineEditorVersion {
    version: string;
    label: string;
    note: string;
    status: 'ready' | 'review' | 'archived';
    savedAt: string;
}

export interface PipelineEditorNodeMetadata {
    summary: string;
    rules: string[];
    observed_structure: string[];
    ontology_classes: string[];
    ontology_relations: string[];
    impact: string;
}

export interface PipelineEditorState {
    draft: PipelineEditorDraft | null;
    source_draft?: PipelineEditorDraft | null;
    source_metadata?: Record<string, PipelineEditorNodeMetadata>;
    history: PipelineEditorVersion[];
}

export interface PipelineEditorValidationResponse {
    ok: boolean;
    validation_status: 'passed' | 'failed';
    validation_message: string;
    violations: string[];
}

export interface ComparedPipeline {
    pipeline_name: string;
    pipeline_type: string;
    pipeline_components: string[];
    pipeline_data_input: string;
    pipeline_data_output: string;
    pipeline_associated_model: string;
}

export interface DashboardSummary {
    models: number;
    datasets: number;
    pipelines: number;
    deployed_models: number;
}

export interface ChatHistoryMessage {
    id: string;
    role: 'user' | 'assistant';
    text: string;
    payload?: unknown;
}

export interface NlqLogEntry {
    request_id: string;
    started_at: string;
    finished_at?: string;
    success: boolean;
    error?: string | null;
    metadata: Record<string, unknown>;
    llm_calls: Array<{
        timestamp: string;
        purpose: string;
        provider?: string | null;
        model?: string | null;
        base_url?: string | null;
        prompt_chars: number;
        messages: Array<Record<string, unknown>>;
        response_text?: string | null;
        error?: string | null;
    }>;
    payload?: Record<string, unknown>;
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

export const getDashboardSummary = async (): Promise<DashboardSummary> => {
    const response = await fetch(buildV1Url('dashboard/summary'));
    if (!response.ok) {
        throw new Error('Failed to load dashboard summary.');
    }
    return await response.json();
}

export const getChatMemory = async (sessionId: string): Promise<ChatHistoryMessage[]> => {
    const response = await fetch(`${buildV1Url('chat-memory')}?session_id=${encodeURIComponent(sessionId)}`);
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to load chat history.');
    }
    const payload = await response.json();
    return payload?.messages ?? [];
}

export const saveChatMemory = async (sessionId: string, messages: ChatHistoryMessage[]): Promise<ChatHistoryMessage[]> => {
    const response = await fetch(buildV1Url('chat-memory'), {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            session_id: sessionId,
            messages,
        }),
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to save chat history.');
    }
    const payload = await response.json();
    return payload?.messages ?? [];
}

export const clearChatMemory = async (sessionId: string): Promise<void> => {
    const response = await fetch(`${buildV1Url('chat-memory')}?session_id=${encodeURIComponent(sessionId)}`, {
        method: 'DELETE',
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to clear chat history.');
    }
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

export const getNlqLogs = async (limit = 20): Promise<NlqLogEntry[]> => {
    const response = await fetch(`${buildV1Url('settings/nlq-logs')}?limit=${limit}`);
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to load NLQ logs.');
    }
    const payload = await response.json();
    return payload?.logs ?? [];
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

export const getPipelineEditorState = async (pipelineName: string): Promise<PipelineEditorState> => {
    const response = await fetch(`${buildV1Url('pipeline-editor/draft')}?pipeline_name=${encodeURIComponent(pipelineName)}`);
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to load pipeline editor state.');
    }
    return await response.json();
}

export const getExistingPipelines = async (searchTerm = ''): Promise<string[]> => {
    const suffix = searchTerm
        ? `?search_term=${encodeURIComponent(searchTerm)}`
        : '';
    const response = await fetch(`${buildV1Url('pipeline-editor/existing')}${suffix}`);
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to load existing pipelines.');
    }
    const payload = await response.json();
    return payload?.pipelines ?? [];
}

export const comparePipelines = async (pipelineNames: string[]): Promise<ComparedPipeline[]> => {
    const params = new URLSearchParams();
    pipelineNames.forEach((name) => params.append('pipeline_name', name));
    const response = await fetch(`${buildV1Url('pipelines/compare')}?${params.toString()}`);
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to compare pipelines.');
    }
    const payload = await response.json();
    return payload?.data ?? [];
}

export const savePipelineDraft = async (draft: PipelineEditorDraft): Promise<PipelineEditorState> => {
    const response = await fetch(buildV1Url('pipeline-editor/save-draft'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(draft),
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to save pipeline draft.');
    }
    return await response.json();
}

export const resetPipelineDraft = async (pipelineName: string): Promise<void> => {
    const response = await fetch(`${buildV1Url('pipeline-editor/draft')}?pipeline_name=${encodeURIComponent(pipelineName)}`, {
        method: 'DELETE',
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to reset pipeline draft.');
    }
}

export const validatePipelineDraft = async (draft: PipelineEditorDraft): Promise<PipelineEditorValidationResponse> => {
    const response = await fetch(buildV1Url('pipeline-editor/validate'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(draft),
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to validate pipeline draft.');
    }
    return await response.json();
}

export const publishPipelineDraft = async (draft: PipelineEditorDraft): Promise<{
    ok: boolean;
    published_at: string;
    version: PipelineEditorVersion;
    draft: PipelineEditorDraft;
    history: PipelineEditorVersion[];
}> => {
    const response = await fetch(buildV1Url('pipeline-editor/publish'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(draft),
    });
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || 'Failed to publish pipeline draft.');
    }
    return await response.json();
}
