import './styles/loadingbar.css';

const LoadingBar = ({isLoading}) => {
    return (
        <div className="loading-bar-container">
            {isLoading && (
                <div className="loading-bar"></div>
            )}
        </div>
    );
};

export default LoadingBar;
