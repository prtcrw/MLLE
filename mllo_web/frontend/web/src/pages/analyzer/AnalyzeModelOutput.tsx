import React, { useState, useEffect } from 'react';
import { buildV1Url } from '../../services/api';
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
    const [availableInputDatasets, setAvailableInputDatasets] = useState<string[]>([]);
    const [availableOutputDatasets, setAvailableOutputDatasets] = useState<string[]>([]);
    const [selectedInputDataset, setSelectedInputDataset] = useState<string>('');
    const [selectedOutputDatasets, setSelectedOutputDatasets] = useState<string[]>([]);

    const fetchAvailableInputDatasets = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(buildV1Url('datasets/model-input-list'));
            const result = await response.json();
            setAvailableInputDatasets(result.datasets);
            if (result.datasets.length > 0) {
                setSelectedInputDataset(result.datasets[0]);
            }
        } catch (error) {
            console.error("Error fetching input datasets", error);
        } finally {
            setIsLoading(false);
        }
    };

    const fetchAvailableOutputDatasets = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(buildV1Url('datasets/model-output-list'));
            const result = await response.json();
            setAvailableOutputDatasets(result.datasets);
            if (result.datasets.length > 0) {
                // Initialize selectedOutputDatasets with the first available dataset
                setSelectedOutputDatasets([result.datasets[0]]);
            }
        } catch (error) {
            console.error("Error fetching output datasets", error);
        } finally {
            setIsLoading(false);
        }
    };

    const fetchData = async () => {
        setIsLoading(true);
        try {
            if (plotType === 'PCA') {
                // PCA logic remains the same
                const url = `datasets/model-pca?input_dataset_name=${selectedInputDataset}&output_dataset_name=${selectedOutputDatasets[0]}`;
                console.log('Fetching PCA data from:', url);
                const response = await fetch(buildV1Url(url));
                const result = await response.json();
                console.log('PCA data received:', result);
                if (!result.results || result.results.length === 0) {
                    console.error('No PCA data received or empty results');
                }
                setInputResults(result.results);
            } else {
                // Updated logic for fetching multiple datasets
                const validDatasets = selectedOutputDatasets.filter(name => name);
                if (validDatasets.length === 0) {
                    console.error('No valid output datasets selected.');
                    setIsLoading(false);
                    return;
                }
    
                // Prepare URL with multiple dataset_names parameters
                const params = validDatasets.map(name => `dataset_names=${encodeURIComponent(name)}`).join('&');
                const url = `datasets/model-output?${params}`;
                console.log(`Fetching ${plotType} data for datasets:`, validDatasets);
                const response = await fetch(buildV1Url(url));
                const result = await response.json();
                console.log(`${plotType} data received:`, result);
                if (!result.results || result.results.length === 0) {
                    console.error(`No ${plotType} data received or empty results`);
                }
                setOutputResults(result.results);
            }
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const renderChart = () => {
        switch (plotType) {
            case 'PCA':
                if (!inputResults) return null;
                return <PCAChart results={inputResults} />;
            case 'PDF':
                if (!outputResults) return null;
                return <PDFChart outputResults={outputResults} />;
            case 'Histogram':
                if (!outputResults) return null;
                return <HistogramChart outputResults={outputResults} />;
            default:
                return null;
        }
    };

    const handlePlot = async () => {
        await fetchData();
    };

    const handlePlotTypeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        const selectedPlotType = event.target.value;
        setPlotType(selectedPlotType);
        if (selectedPlotType === 'PCA') {
            fetchAvailableInputDatasets();
        }
        fetchAvailableOutputDatasets();
    };

    const handleInputDatasetChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
        setSelectedInputDataset(event.target.value);
    };

    const handleOutputDatasetChange = (index: number) => (event: React.ChangeEvent<HTMLSelectElement>) => {
        const newSelectedOutputDatasets = [...selectedOutputDatasets];
        newSelectedOutputDatasets[index] = event.target.value;
        setSelectedOutputDatasets(newSelectedOutputDatasets);
    };

    const handleAddOutputDataset = () => {
        if (availableOutputDatasets.length > 0) {
            setSelectedOutputDatasets([...selectedOutputDatasets, availableOutputDatasets[0]]);
        } else {
            console.error('No available output datasets to add.');
        }
    };

    const handleRemoveOutputDataset = (index: number) => () => {
        const newSelectedOutputDatasets = selectedOutputDatasets.filter((_, i) => i !== index);
        setSelectedOutputDatasets(newSelectedOutputDatasets);
    };

    useEffect(() => {
        if (plotType === 'PCA') {
            fetchAvailableInputDatasets();
        }
        fetchAvailableOutputDatasets();
    }, [plotType]);

    return (
        <>
            <LoadingBar isLoading={isLoading} />
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

                    {plotType === 'PCA' && (
                        <div className="filter-item">
                            <label>
                                Select Input Dataset:
                                <select value={selectedInputDataset} onChange={handleInputDatasetChange}>
                                    {availableInputDatasets.map((dataset, index) => (
                                        <option key={index} value={dataset}>
                                            {dataset}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        </div>
                    )}

                    {selectedOutputDatasets.map((selectedDataset, index) => (
                        <div key={index} className="filter-item output-dataset-selection">
                            <label>
                                Select Output Dataset {index + 1}:
                                <select value={selectedDataset} onChange={handleOutputDatasetChange(index)}>
                                    {availableOutputDatasets.map((availableDataset, datasetIndex) => (
                                        <option key={datasetIndex} value={availableDataset}>
                                            {availableDataset}
                                        </option>
                                    ))}
                                </select>
                            </label>
                            {index > 0 && (
                                <button onClick={handleRemoveOutputDataset(index)} className="remove-dataset-btn">
                                    Remove
                                </button>
                            )}
                        </div>
                    ))}

                    {plotType !== 'PCA' && (
                        <div className="filter-item">
                            <button onClick={handleAddOutputDataset} className="add-dataset-btn">
                                Add Output Dataset
                            </button>
                        </div>
                    )}

                    <div className="filter-item">
                        <button onClick={handlePlot} className="plot-btn">
                            {plotType === 'PCA' ? 'Load Data' : 'Load Output Data'}
                        </button>
                    </div>
                </div>
                {((inputResults && plotType === 'PCA') || (outputResults && plotType !== 'PCA')) && (
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
