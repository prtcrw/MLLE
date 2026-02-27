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
