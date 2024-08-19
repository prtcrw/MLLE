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