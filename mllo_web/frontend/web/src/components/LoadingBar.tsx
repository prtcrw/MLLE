import React from "react";
import './styles/loadingbar.css';

interface LoadingBarProps {
    isLoading: boolean;
}

const LoadingBar: React.FC<LoadingBarProps> = ({isLoading}) => {
    return (
        <div className="loading-bar-container">
            {isLoading && <div className="loading-bar"></div>}
        </div>
    );
};

export default LoadingBar;
