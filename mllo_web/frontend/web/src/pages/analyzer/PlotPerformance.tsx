import React, {useEffect, useState} from 'react';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import {Bar, Line} from 'react-chartjs-2';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import {
    BarElement,
    CategoryScale,
    Chart as ChartJS,
    Legend,
    LinearScale,
    LineElement,
    PointElement,
    Title,
    Tooltip
} from 'chart.js';
import './styles/plotperformance.css';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend, ChartDataLabels);

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
    const [fetchedData, setFetchedData] = useState<PerformanceMetrics>({});
    const [data, setData] = useState<any>(null);
    const [yAxisMetricOptions, setYAxisMetricOptions] = useState<string[]>([]);
    const [minCutoff, setMinCutoff] = useState(0.0);
    const [maxCutoff, setMaxCutoff] = useState(100.0);

    useEffect(() => {
        fetchData();
    }, []);

    useEffect(() => {
        if (yAxisMetric && orderBy && groupBy) {
            updateCutoffValues();
            drawChart();
        }
    }, [yAxisMetric, orderBy, groupBy]);

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

    const drawChart = async () => {
        setIsLoading(true); // Set loading to true
        try {
            // Prepare the chart data
            const chartData = {
                labels: fetchedData[yAxisMetric].map(item => item.datasetName),
                datasets: [{
                    label: yAxisMetric.charAt(0).toUpperCase() + yAxisMetric.slice(1), // Capitalize the label
                    data: fetchedData[yAxisMetric].map(item => item.modelPerformanceValue),
                    backgroundColor: plotType === 'Bar' ? 'rgba(75, 192, 192, 0.2)' : 'rgba(153, 102, 255, 0.2)',
                    borderColor: plotType === 'Bar' ? 'rgba(75, 192, 192, 1)' : 'rgba(153, 102, 255, 1)',
                    borderWidth: 1,
                    fill: plotType === 'Line', // Fill the area under the line only if it's a Line chart
                }]
            };

            // Sort the chart data based on orderBy and groupBy
            const sortedData = sortChartData(chartData, orderBy, groupBy);
            setData(sortedData);
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    };

    const sortChartData = (chartData: any, orderBy: string, groupBy: string) => {
        // Sort the data based on orderBy and groupBy
        const data = chartData.datasets[0].data as PerformanceData[];
        const sortedData = data.map((item, index) => ({
            datasetName: chartData.labels[index],
            modelPerformanceValue: item,
        }));

        if (groupBy === 'datasetName') {
            sortedData.sort((a, b) => {
                if (orderBy === 'Ascending') {
                    return a.datasetName.localeCompare(b.datasetName);
                } else {
                    return b.datasetName.localeCompare(a.datasetName);
                }
            });
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
                </div>
                <div className="plot-section" style={{width: '65%'}}>
                    <h2>Plot</h2>
                    {data && (
                        plotType === 'Bar' ? (
                            <Bar data={data} options={{
                                responsive: true,
                                plugins: {
                                    legend: {position: 'top'},
                                    tooltip: {callbacks: {label: (context) => `${context.dataset.label}: ${context.raw}`}}
                                }
                            }}/>
                        ) : (
                            <Line data={data} options={{
                                responsive: true,
                                plugins: {
                                    legend: {position: 'top'},
                                    tooltip: {callbacks: {label: (context) => `${context.dataset.label}: ${context.raw}`}}
                                }
                            }}/>
                        )
                    )}
                </div>
            </div>
        </>
    );
};

export default PlotPerformance;
