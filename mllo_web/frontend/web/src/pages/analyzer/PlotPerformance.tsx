import React, {useEffect, useState} from 'react';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import {Bar, Line} from 'react-chartjs-2';
import {
    BarElement,
    CategoryScale,
    Chart as ChartJS,
    Legend,
    LinearScale,
    LineElement,
    Filler,
    PointElement,
    Title,
    Tooltip
} from 'chart.js';
import './styles/plot_performance.css';
import ChartDataLabels from "chartjs-plugin-datalabels";

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, Filler, PointElement, Title, Tooltip, Legend);

type PerformanceData = {
    datasetName: string;
    modelPerformanceValue: number;
}

type PerformanceMetrics = {
    [metric: string]: PerformanceData[];
};

// Convert snake_case to camelCase
const convertToCamelCase = (data: any): PerformanceMetrics => {
    const camelCaseData: PerformanceMetrics = {};

    for (const metric in data) {
        if (data.hasOwnProperty(metric)) {
            camelCaseData[metric] = data[metric].map((item: any) => ({
                datasetName: item['dataset_name'],
                modelPerformanceValue: parseFloat(item['model_performance_value']),
            }));
        }
    }

    return camelCaseData;
};

const PlotPerformance: React.FC = () => {
    const [plotType, setPlotType] = useState('Bar');
    const [yAxisMetric, setYAxisMetric] = useState(''); // Initially empty
    const [performanceCutoff, setPerformanceCutoff] = useState(50);
    const [orderBy, setOrderBy] = useState('Ascending');
    const [groupBy, setGroupBy] = useState('datasetName');
    const [isLoading, setIsLoading] = useState(false);
    const [fetchedData, setFetchedData] = useState<PerformanceMetrics>(null);
    const [data, setData] = useState<any>(null);
    const [options, setOptions] = useState<any>({});
    const [yAxisMetricOptions, setYAxisMetricOptions] = useState<string[]>([]);
    const [minCutoff, setMinCutoff] = useState(0.0);
    const [maxCutoff, setMaxCutoff] = useState(100.0);

    useEffect(() => {
        if (yAxisMetric && performanceCutoff && orderBy && groupBy) {
            updateCutoffValues();
            drawChart();
        }
    }, [yAxisMetric, performanceCutoff, orderBy, groupBy]);

    const fetchData = async () => {
        setIsLoading(true); // Set loading to true
        try {
            // Fetch data with filters
            const response = await fetch(buildV1Url(`datasets/performances`));
            let fetchedData = await response.json();
            fetchedData = convertToCamelCase(fetchedData['model_performance_metric']);
            setFetchedData(fetchedData);

            // Extract the first metric key as the default yAxisMetric
            const initialMetric = Object.keys(fetchedData)[0];
            setYAxisMetric(initialMetric);
            setYAxisMetricOptions(Object.keys(fetchedData));
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    };

    const calculateVariance = (values: number[]): number => {
        const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
        const variance = values.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / values.length;
        return variance;
    };

    const drawChart = async () => {
        setIsLoading(true); // Set loading to true
        try {
            // Prepare the chart data
            const filteredData = fetchedData[yAxisMetric].filter(item => item.modelPerformanceValue >= performanceCutoff) as PerformanceData[];

            const chartData = {
                labels: filteredData.map(item => item.datasetName),
                datasets: [{
                    label: yAxisMetric.charAt(0).toUpperCase() + yAxisMetric.slice(1), // Capitalize the label
                    data: filteredData.map(item => item.modelPerformanceValue),
                    backgroundColor: plotType === 'Bar' ? 'rgba(75, 192, 192, 0.2)' : 'rgba(153, 102, 255, 0.2)',
                    borderColor: plotType === 'Bar' ? 'rgba(75, 192, 192, 1)' : 'rgba(153, 102, 255, 1)',
                    borderWidth: 1,
                    fill: plotType === 'Line', // Fill the area under the line only if it's a Line chart
                }]
            };

            // Sort the chart data based on orderBy and groupBy
            const sortedData = sortChartData(chartData, orderBy, groupBy);
            setData(sortedData);

            // Update the chart options with dynamic yAxis min and max values
            const dataValues = fetchedData[yAxisMetric].map(item => item.modelPerformanceValue);
            const minY = Math.min(...dataValues);
            const maxY = Math.max(...dataValues);

            // Calculate variance and standard deviation
            const variance = calculateVariance(dataValues);
            const standardDeviation = Math.sqrt(variance);

            // Adjust min and max values
            const adjustmentFactor = 1; // Adjust this factor if needed (e.g., 1.5 for more range)
            const adjustedMinY = minY - adjustmentFactor * standardDeviation;
            const adjustedMaxY = maxY + adjustmentFactor * standardDeviation;

            const chartOptions = {
                responsive: true,
                plugins: {
                    legend: {position: 'top'},
                    tooltip: {
                        callbacks: {
                            label: (context: any) => `${context.dataset.label}: ${context.raw}`
                        }
                    },
                    datalabels: {
                        anchor: 'end',
                        align: 'end',
                        clamp: true
                    }
                },
                scales: {
                    y: {
                        min: adjustedMinY,
                        max: adjustedMaxY,
                    }
                }
            };

            setOptions(chartOptions);
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    };

    const sortChartData = (chartData: any, orderBy: string, groupBy: string) => {
        // Sort the data based on orderBy and groupBy
        const data = chartData.datasets[0].data as number[];
        const sortedData = data.map((item, index) => ({
            datasetName: chartData.labels[index],
            modelPerformanceValue: item,
        }));

        // Sort by modelPerformanceValue
        sortedData.sort((a, b) => {
            if (orderBy === 'Ascending') {
                return a.modelPerformanceValue - b.modelPerformanceValue;
            } else {
                return b.modelPerformanceValue - a.modelPerformanceValue;
            }
        });

        if (groupBy) {
            // TODO: ...
        }

        // Update labels and data in the chartData object
        chartData.labels = sortedData.map(item => item.datasetName);
        chartData.datasets[0].data = sortedData.map(item => item.modelPerformanceValue);

        return chartData;
    };

    const updateCutoffValues = () => {
        const values = fetchedData[yAxisMetric].map(item => item.modelPerformanceValue);
        const minModelPerformanceValue = Math.min(...values);
        const maxModelPerformanceValue = Math.max(...values);

        setMinCutoff(minModelPerformanceValue);
        setMaxCutoff(maxModelPerformanceValue);

        if (performanceCutoff < minModelPerformanceValue || performanceCutoff > maxModelPerformanceValue) {
            setPerformanceCutoff(minModelPerformanceValue);
        }
    };

    const handleYAxisMetricChange = (metric: string) => {
        setYAxisMetric(metric);
        updateCutoffValues();
    };

    const handleLoadDataset = async () => {
        await fetchData();
    }

    return (
        <>
            <LoadingBar isLoading={isLoading}/>
            <div className="plot-performance-container">
                <div className="filters-section">
                    <h2>Filters</h2>
                    <div className="filter-item">
                        <label>
                            Plot Type:
                            <select value={plotType} onChange={(e) => setPlotType(e.target.value)}>
                                <option value="Bar">Bar</option>
                                <option value="Line">Line</option>
                                {/* Add more plot types as needed */}
                            </select>
                        </label>
                    </div>
                    {(fetchedData) && (
                        <div className="filter-item">
                            <label>
                                Y axis (Performance Metric):
                                <select value={yAxisMetric} onChange={(e) => handleYAxisMetricChange(e.target.value)}>
                                    {yAxisMetricOptions.map(metric => (
                                        <option key={metric}
                                                value={metric}>{metric.charAt(0).toUpperCase() + metric.slice(1)}</option>
                                    ))}
                                </select>
                            </label>
                        </div>
                    )}
                    {(fetchedData) && (
                        <div className="filter-item">
                            <label>
                                Performance Cutoff:
                                <input
                                    type="range"
                                    min={minCutoff}
                                    max={maxCutoff}
                                    value={performanceCutoff}
                                    step={0.01}
                                    onChange={(e) => setPerformanceCutoff(Number(e.target.value))}
                                    className="range-slider"
                                />
                                <span className="cutoff-value">{performanceCutoff.toFixed(2)}</span>
                            </label>
                        </div>
                    )}
                    <div className="filter-item">
                        <label>
                            Order By:
                            <select value={orderBy} onChange={(e) => setOrderBy(e.target.value)}>
                                <option value="Ascending">Ascending</option>
                                <option value="Descending">Descending</option>
                            </select>
                        </label>
                    </div>
                    <div className="filter-item">
                        <label>
                            Group By:
                            <select value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
                                <option value="datasetName">Dataset Name</option>
                            </select>
                        </label>
                    </div>
                    <div className="filter-item">
                        <button onClick={handleLoadDataset}>Load Dataset</button>
                    </div>
                </div>
                {data && (
                    <div className="plot-section">
                        <h2>Plot</h2>
                        {plotType === 'Bar' ? (
                            <Bar data={data} plugins={[ChartDataLabels]} options={options}/>
                        ) : (
                            <Line data={data} plugins={[ChartDataLabels]} options={options}/>
                        )}
                    </div>
                )}
            </div>
        </>
    );
};

export default PlotPerformance;
