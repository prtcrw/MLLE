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

export const convertEnglishToSparql = async (input: string, endpoint?: string): Promise<string> => {
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
        const text = await resp.text();
        throw new Error(`Conversion failed: ${resp.status} ${text}`);
    }

    // Try json { sparql: '...' } or plain text
    const contentType = resp.headers.get('Content-Type') || '';
    if (contentType.includes('application/json')) {
        const j = await resp.json();
        if (j && typeof j.sparql === 'string') return j.sparql;
        if (j && typeof j.result === 'string') return j.result;
        return JSON.stringify(j);
    }

    return await resp.text();
}