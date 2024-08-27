export const pascalCaseToWords = (text: string): string => {
    return text
        .replace(/([a-z])([A-Z])/g, '$1 $2')  // Add space between lowercase and uppercase
        .replace(/([A-Z]+)([A-Z][a-z0-9])/g, '$1 $2')  // Handle consecutive uppercase letters followed by lowercase letters or numbers
        .replace(/([a-zA-Z])([0-9])/g, '$1 $2')  // Add space between letters and numbers
        .replace(/([0-9])([a-zA-Z])/g, '$1 $2');  // Add space between numbers and letters
};

export const lowercaseToPascalCase = (text: string): string => {
    return text
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
};