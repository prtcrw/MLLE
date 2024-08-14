import React from "react";
import './styles/loadingbar.css';

interface LoadingBarProps {
    isLoading: boolean;
}

const LoadingBar: React.FC<LoadingBarProps> = ({isLoading}) => {
    const visibilityClass = isLoading ? '' : 'hidden';
    return (
        <div className={`loading-bar-container ${visibilityClass}`}>
            {isLoading && <div className="loading-bar"></div>}
        </div>
    );
};

export default LoadingBar;
