import React, {useEffect, useRef, useState} from 'react';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import {
    BarElement,
    CategoryScale,
    Chart,
    Legend,
    LinearScale,
    PointElement,
    Title,
    Tooltip,
} from 'chart.js';
import './styles/analyze_model_output.css';

// Register Chart.js components
Chart.register(CategoryScale, LinearScale, BarElement, PointElement, Title, Tooltip, Legend);


const AnalyzeModelOutput: React.FC = () => {
    const [plotType, setPlotType] = useState('scatter');
    const [isLoading, setIsLoading] = useState(false);
    const [metadata, setMetadata] = useState<any>(null);
    const [data, setData] = useState<any>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setIsLoading(true); // Set loading to true
        try {
            // Fetch data with filters
            const response = await fetch(buildV1Url(`datasets/model-output`));
            const result = await response.json();
            setMetadata(result.metadata);
            setData(result.data);
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    };

    // Assuming you have a reference to a canvas element
    const chartRef = useRef(null);

    useEffect(() => {
        if (data && metadata && chartRef.current) {
            const ctx = chartRef.current.getContext('2d');

            const chartConfig = {
                type: plotType, // Use the state variable
                data: {},
                options: {},
            };

            // Update data based on plot type (explained below)
            updateChartData(data, metadata, chartConfig);

            const chart = new Chart(ctx, chartConfig);

            return () => {
                chart.destroy();
            };
        }
    }, [data, metadata, chartRef, plotType]);

    const updateChartData = (data, metadata, chartConfig) => {
        if (chartConfig.type === 'scatter') {
            // Existing scatter plot data logic (unchanged)
            chartConfig.data = {
                datasets: metadata.labels.map((label, i) => ({
                    label,
                    data: data.filter(point => point.label === label),
                    backgroundColor: `rgba(${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, 0.7)`,
                    borderColor: `rgba(${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, 1)`,
                    borderWidth: 0,
                })),
            };
        } else if (chartConfig.type === 'bar') {
            // Count occurrences of each label
            const labelCounts = data.reduce((counts, point) => {
                counts[point.label] = (counts[point.label] || 0) + 1;
                return counts;
            }, {});

            // Create histogram data based on counts
            const histogramData = metadata.labels.map(label => labelCounts[label] || 0);

            chartConfig.data = {
                labels: metadata.labels,
                datasets: [{
                    label: 'Frequency',
                    data: histogramData,
                    backgroundColor: `rgba(${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, 0.7)`,
                    borderColor: `rgba(${Math.floor(Math.random()
                        * 256)}, ${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, 1)`,
                    borderWidth: 0,
                }],
            };
        }
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
                            <select value={plotType} onChange={(e) => setPlotType(e.target.value)}>
                                <option value="scatter">Scatter</option>
                                <option value="bar">Bar</option>
                            </select>
                        </label>
                    </div>
                </div>
                <div className="plot-section" style={{width: '65%'}}>
                    <h2>Plot</h2>
                    <canvas ref={chartRef}/>
                </div>
            </div>
        </>
    );
};

export default AnalyzeModelOutput;
