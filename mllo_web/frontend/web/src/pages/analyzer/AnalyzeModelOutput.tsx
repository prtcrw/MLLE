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
    const [results, setResults] = useState<any>(null);

    const fetchData = async () => {
        setIsLoading(true); // Set loading to true
        try {
            // Fetch data with filters
            const url = plotType === 'PCA' ? 'datasets/model-input' : 'datasets/model-output';
            const response = await fetch(buildV1Url(url));
            const result = await response.json();
            setResults(result.results);
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    };

    const renderChart = () => {
        if (!results) return null;

        switch (plotType) {
            case 'PCA':
                return <PCAChart results={results} />;
            case 'PDF':
                return <PDFChart results={results} />;
            case 'Histogram':
                return <HistogramChart results={results} />;
            default:
                return null;
        }
    };

    const handlePlot = () => {
        fetchData();
    };

    const handlePlotTypeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        setPlotType(event.target.value);
        setResults(null);
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
                        <button onClick={handlePlot}>Plot</button>
                    </div>
                </div>
                <div className="plot-section" style={{width: '65%'}}>
                    <h2>Plot</h2>
                    {results && renderChart()}
                </div>
            </div>
        </>
    );
};

export default AnalyzeModelOutput;
