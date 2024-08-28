import React, {useState} from 'react';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import './styles/analyze_model_output.css';
import PCAChart from "../../charts/PCAChart.tsx";
import PDFChart from "../../charts/PDFChart.tsx";
import HistogramChart from "../../charts/HistogramChart.tsx";


const AnalyzeModelOutput: React.FC = () => {
    const [plotType, setPlotType] = useState('PCA');
    const [isLoading, setIsLoading] = useState(false);
    const [inputResults, setInputResults] = useState<any>(null);
    const [outputResults, setOutputResults] = useState<any>(null);

    const fetchData = async () => {
        setIsLoading(true); // Set loading to true
        try {
            // Fetch data with filters
            const url = plotType === 'PCA' ? 'datasets/model-input' : 'datasets/model-output';
            const response = await fetch(buildV1Url(url));
            const result = await response.json();
            if (plotType === 'PCA') {
                setInputResults(result.results);
            } else {
                setOutputResults(result.results);
            }

        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    };

    const renderChart = () => {
        switch (plotType) {
            case 'PCA':
                if (!inputResults) return null;
                return <PCAChart results={inputResults}/>;
            case 'PDF':
                if (!outputResults) return null;
                return <PDFChart results={outputResults}/>;
            case 'Histogram':
                if (!outputResults) return null;
                return <HistogramChart results={outputResults}/>;
            default:
                return null;
        }
    };

    const handlePlot = async () => {
        await fetchData();
    };

    const handlePlotTypeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        setPlotType(event.target.value);
    };

    return (
        <>
            <LoadingBar isLoading={isLoading}/>
            <div className="analyze-model-output-container">
                <div className="filters-section">
                    <h2>Filters</h2>
                    <div className="filter-item">
                        <label>
                            Plot Type:
                            <select value={plotType} onChange={handlePlotTypeChange}>
                                <option value="PCA">PCA</option>
                                <option value="PDF">PDF</option>
                                <option value="Histogram">Histogram</option>
                            </select>
                        </label>
                    </div>
                    <div className="filter-item">
                        {(plotType == 'PCA') && (
                            <button onClick={handlePlot}>Load Raw Data</button>
                        )}
                        {(plotType != 'PCA') && (
                            <button onClick={handlePlot}>Load Output Data</button>
                        )}
                    </div>
                </div>
                {((inputResults && plotType == 'PCA') || (outputResults && plotType != 'PCA')) && (
                    <div className="plot-section">
                        <h2>Plot</h2>
                        {renderChart()}
                    </div>
                )}
            </div>
        </>
    );
};

export default AnalyzeModelOutput;
