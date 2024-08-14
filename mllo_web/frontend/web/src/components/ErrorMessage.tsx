// Error.tsx
import React from 'react';

interface ErrorProps {
    message: string;
}

const ErrorMessage: React.FC<ErrorProps> = ({message}) => {
    return (
        <div className="alert alert-danger" role="alert">
            {message}
        </div>
    );
};

export default ErrorMessage;
