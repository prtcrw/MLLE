import React, {ReactNode, useEffect, useMemo, useState} from 'react';
import {DownloadIcon} from '../../components/Icons';
import {
    clearChatMemory,
    getChatMemory,
    getSettings,
    listSettingsRepos,
    NLQResponse,
    queryNaturalLanguage,
    saveChatMemory
} from '../../services/api';
import './styles/plot_performance.css';

type AnswerMode = 'exact' | 'conceptual' | 'auto';
type ResultValue = string | null | string[];
type ResultRow = Record<string, ResultValue>;

interface ChatAssistantPayload {
    answer: string;
    sparql: string;
    results: ResultRow[];
    repo_used: string;
    inference_used: boolean;
    intent: {
        tool: string;
        reasoning: string;
    };
}

interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    text: string;
    payload?: ChatAssistantPayload;
}

const CHAT_SESSION_ID = 'chat-with-mllo-main';

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

        if (i + 1 < lines.length && lines[i].includes('|') && isMarkdownSeparator(lines[i + 1])) {
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
                                <th key={index}
                                    style={{border: '1px solid #d7d7d7', padding: '0.55rem', background: '#f5f5f5', textAlign: 'left'}}>
                                    {renderInlineMarkdown(header)}
                                </th>
                            ))}
                        </tr>
                        </thead>
                        <tbody>
                        {rows.map((row, rowIndex) => (
                            <tr key={rowIndex}>
                                {headers.map((_, colIndex) => (
                                    <td key={colIndex}
                                        style={{border: '1px solid #e7e7e7', padding: '0.55rem', verticalAlign: 'top'}}>
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

const downloadCsv = (rows: ResultRow[], columns: string[], filename: string): void => {
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
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.setAttribute('download', filename);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
};

const makeId = (): string => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const buildContextualQuestion = (messages: ChatMessage[], currentQuestion: string): string => {
    const recent = messages.slice(-4);
    if (recent.length === 0) {
        return currentQuestion;
    }
    const transcript = recent
        .map((message) => `${message.role === 'user' ? 'User' : 'Assistant'}: ${message.text}`)
        .join('\n');
    return [
        'Conversation context:',
        transcript,
        '',
        `Current user question: ${currentQuestion}`,
        'Resolve references to earlier turns when needed. If the current question stands on its own, prioritize the current question.',
    ].join('\n');
};

const examplePrompts = [
    'What kinds of models exist in MLLO?',
    'Show me models trained on MNIST.',
    'Which datasets are used as test data sets?',
    'Show me deployed models and the systems they run on.',
    'Show me models with performance more than 0.9.',
    'Show me models with performance more than 0.9 and their test dataset.',
    'Show me models with performance more than 0.9, their test dataset, and their pipeline.',
    'What is the best performing model?',
    'Show me the best performing model and its pipeline.',
    'Which pipeline is associated with the best performing model?',
    'Compare pipelines PreprocessingPipeline1 and PreprocessingPipeline10.',
    'Show me datasets related to MLModel1.',
    'Show me pipelines associated with MLModel1.',
    'What raw dataset is used to make PreprocessedDataset1?',
    'What was used to create PreprocessedDataset1?',
    'Trace the lineage of PreprocessedDataset1 upstream.',
    'Which pipeline produced PreprocessedDataset1?',
    'What downstream artifacts use MnistG16?',
    'Trace the lineage of MnistG16 downstream.',
];

const ChatWithMLLO: React.FC = () => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [repos, setRepos] = useState<string[]>([]);
    const [selectedRepo, setSelectedRepo] = useState('');
    const [answerMode, setAnswerMode] = useState<AnswerMode>('auto');
    const [selectedExample, setSelectedExample] = useState('');
    const [chatReady, setChatReady] = useState(false);

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
        const loadHistory = async () => {
            try {
                const history = await getChatMemory(CHAT_SESSION_ID);
                if (Array.isArray(history)) {
                    setMessages(history as ChatMessage[]);
                }
            } catch {
                // ignore
            } finally {
                setChatReady(true);
            }
        };
        void loadHistory();
    }, []);

    useEffect(() => {
        if (!chatReady) {
            return;
        }
        const persist = async () => {
            try {
                await saveChatMemory(CHAT_SESSION_ID, messages);
            } catch {
                // ignore persistence errors in UI state
            }
        };
        void persist();
    }, [chatReady, messages]);

    const canSend = input.trim().length > 0 && !loading;

    const handleClear = () => {
        const clear = async () => {
            setMessages([]);
            setError(null);
            try {
                await clearChatMemory(CHAT_SESSION_ID);
            } catch {
                // ignore
            }
        };
        void clear();
    };

    const handleSend = async () => {
        const trimmed = input.trim();
        if (!trimmed) return;

        const userMessage: ChatMessage = {
            id: makeId(),
            role: 'user',
            text: trimmed,
        };
        const baseMessages = [...messages, userMessage];
        setMessages(baseMessages);
        setInput('');
        setLoading(true);
        setError(null);

        try {
            const contextualQuestion = buildContextualQuestion(messages, trimmed);
            const response: NLQResponse = await queryNaturalLanguage(contextualQuestion, selectedRepo, answerMode);
            const assistantMessage: ChatMessage = {
                id: makeId(),
                role: 'assistant',
                text: response.answer,
                payload: {
                    answer: response.answer,
                    sparql: response.sparql,
                    results: response.results,
                    repo_used: response.repo_used,
                    inference_used: response.inference_used,
                    intent: {
                        tool: response.intent.tool,
                        reasoning: response.intent.reasoning,
                    },
                },
            };
            setMessages([...baseMessages, assistantMessage]);
        } catch (err) {
            setError((err as Error).message);
        } finally {
            setLoading(false);
        }
    };

    const disabledRepoSelect = repos.length === 0 || loading;
    const introMessage = useMemo<ChatMessage>(() => ({
        id: 'intro',
        role: 'assistant',
        text: 'Ask about MLLO classes, pipelines, models, datasets, and the demo instances in the selected repository. I will use the existing MLLO query tools and show the evidence for each answer.',
    }), []);

    const chatMessages = messages.length > 0 ? messages : [introMessage];

    return (
        <div className="page-container" style={{display: 'flex', flexDirection: 'column', gap: '1rem', minHeight: 'calc(100vh - 140px)'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap'}}>
                <div>
                    <h2>Chat with MLLO</h2>
                    <p>Ask conversational questions about the MLLO ontology and the demo instances in GraphDB.</p>
                </div>
                <button type="button" onClick={handleClear} disabled={loading || messages.length === 0}>
                    New Chat
                </button>
            </div>

            <div style={{display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem'}}>
                <label style={{display: 'flex', flexDirection: 'column', minWidth: '220px'}}>
                    Repository
                    <select value={selectedRepo} onChange={(e) => setSelectedRepo(e.target.value)} disabled={disabledRepoSelect}>
                        {repos.map((repo) => (
                            <option key={repo} value={repo}>{repo}</option>
                        ))}
                    </select>
                </label>
                <label style={{display: 'flex', flexDirection: 'column', minWidth: '220px'}}>
                    Answer Mode
                    <select value={answerMode} onChange={(e) => setAnswerMode(e.target.value as AnswerMode)} disabled={loading}>
                        <option value="exact">Exact</option>
                        <option value="conceptual">Conceptual</option>
                        <option value="auto">Auto</option>
                    </select>
                </label>
            </div>

            <div style={{display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem', alignItems: 'flex-end'}}>
                <label style={{display: 'flex', flexDirection: 'column', minWidth: '320px', flex: '1 1 420px'}}>
                    Chat example
                    <select
                        value={selectedExample}
                        onChange={(event) => {
                            const next = event.target.value;
                            setSelectedExample(next);
                            if (next) {
                                setInput(next);
                            }
                        }}
                        disabled={loading}
                    >
                        <option value="">Select an example question</option>
                        {examplePrompts.map((prompt) => (
                            <option key={prompt} value={prompt}>{prompt}</option>
                        ))}
                    </select>
                </label>
                <button
                    type="button"
                    className="button"
                    onClick={() => {
                        setInput(selectedExample);
                    }}
                    disabled={loading || !selectedExample}
                    style={{fontSize: '0.84rem'}}
                >
                    Use Example
                </button>
            </div>

            <div style={{display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0}}>
                <div style={{flex: 1, minHeight: 0, overflowY: 'auto', border: '1px solid #ddd', borderRadius: '14px', padding: '1rem', background: '#fbfbfb'}}>
                    <div style={{display: 'flex', flexDirection: 'column', gap: '0.9rem'}}>
                        {chatMessages.map((message) => {
                            const columns = message.payload?.results?.length ? Object.keys(message.payload.results[0]) : [];
                            return (
                                <div
                                    key={message.id}
                                    style={{
                                        alignSelf: message.role === 'user' ? 'flex-end' : 'stretch',
                                        maxWidth: message.role === 'user' ? '78%' : '100%',
                                        background: message.role === 'user' ? '#0f766e' : '#f7f7f7',
                                        color: message.role === 'user' ? '#fff' : '#111',
                                        border: message.role === 'user' ? 'none' : '1px solid #ddd',
                                        borderRadius: '12px',
                                        padding: '0.95rem 1rem',
                                    }}
                                >
                                    <div style={{fontSize: '0.8rem', opacity: 0.8, marginBottom: '0.35rem'}}>
                                        {message.role === 'user' ? 'You' : 'MLLO'}
                                    </div>

                                    {message.role === 'assistant' ? (
                                        <div>{renderMarkdownAnswer(message.text)}</div>
                                    ) : (
                                        <div style={{lineHeight: 1.5}}>{message.text}</div>
                                    )}

                                    {message.payload && (
                                        <div style={{marginTop: '0.9rem', color: '#111'}}>
                                            <div style={{display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.86rem', marginBottom: '0.65rem'}}>
                                                <span>Repository: <strong>{message.payload.repo_used}</strong></span>
                                                <span>Inference: <strong>{message.payload.inference_used ? 'On' : 'Off'}</strong></span>
                                                <span>Rows: <strong>{message.payload.results.length}</strong></span>
                                            </div>

                                            <details>
                                                <summary>Debug Info</summary>
                                                <div style={{marginTop: '0.5rem'}}>
                                                    <div><strong>Intent Tool:</strong> {message.payload.intent.tool}</div>
                                                    <div><strong>Reasoning:</strong> {message.payload.intent.reasoning}</div>
                                                </div>
                                            </details>

                                            {message.payload.results.length > 0 && (
                                                <details style={{marginTop: '0.75rem'}}>
                                                    <summary>Result Table</summary>
                                                    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem', gap: '0.5rem', flexWrap: 'wrap'}}>
                                                        <div style={{fontSize: '0.9rem'}}>Evidence rows</div>
                                                        <button
                                                            type="button"
                                                            onClick={() => downloadCsv(message.payload!.results, columns, `mllo_chat_${message.id}.csv`)}
                                                            style={{display: 'inline-flex', alignItems: 'center', gap: '0.35rem'}}
                                                        >
                                                            <DownloadIcon width={16} height={16}/>
                                                            Export CSV
                                                        </button>
                                                    </div>
                                                    <div style={{overflowX: 'auto', marginTop: '0.75rem'}}>
                                                        <table style={{width: '100%', minWidth: 'max-content', borderCollapse: 'collapse', fontFamily: 'monospace', fontSize: '0.84rem', background: '#fff'}}>
                                                            <thead>
                                                            <tr>
                                                                {columns.map((column) => (
                                                                    <th key={column}
                                                                        style={{border: '1px solid #ccc', padding: '7px 10px', background: '#f5f5f5', textAlign: 'left', whiteSpace: 'nowrap'}}>
                                                                        {column}
                                                                    </th>
                                                                ))}
                                                            </tr>
                                                            </thead>
                                                            <tbody>
                                                            {message.payload.results.map((row, rowIndex) => (
                                                                <tr key={rowIndex}>
                                                                    {columns.map((column) => (
                                                                        <td key={column}
                                                                            style={{border: '1px solid #eee', padding: '8px 10px', maxWidth: '520px', whiteSpace: 'normal', wordBreak: 'break-word', verticalAlign: 'top'}}>
                                                                            <div style={{display: 'flex', flexDirection: 'column', gap: '0.2rem'}}>
                                                                                {normalizeCellLines(row[column]).map((line, index) => (
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
                                                </details>
                                            )}

                                            {message.payload.sparql && (
                                                <details style={{marginTop: '0.75rem'}}>
                                                    <summary>SPARQL</summary>
                                                    <textarea
                                                        value={message.payload.sparql}
                                                        readOnly
                                                        rows={12}
                                                        style={{width: '100%', marginTop: '0.75rem', fontFamily: 'monospace'}}
                                                    />
                                                </details>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {loading && <div>Thinking…</div>}
            {error && <div style={{color: 'red', marginBottom: '0.75rem'}}>Error: {error}</div>}

            <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about MLLO classes, instances, pipelines, models, datasets, or follow up on earlier answers..."
                    rows={5}
                    style={{width: '100%', fontFamily: 'inherit'}}
                />
                <div style={{display: 'flex', gap: '0.5rem', flexWrap: 'wrap'}}>
                    <button type="button" onClick={handleSend} disabled={!canSend}>
                        Send
                    </button>
                    <button type="button" onClick={() => setInput('')} disabled={loading || input.length === 0}>
                        Clear Input
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChatWithMLLO;
