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
    modelName: string;
    modelType: string;
    rawData: string;
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
                modelName: item['model_name'],
                modelType: item['model_type'],
                rawData: item['raw_data'],
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
    const [groupBy, setGroupBy] = useState('default');
    const [isLoading, setIsLoading] = useState(false);
    const [fetchedData, setFetchedData] = useState<PerformanceMetrics | null>(null);
    const [data, setData] = useState<any>(null);
    const [options, setOptions] = useState<any>({});
    const [yAxisMetricOptions, setYAxisMetricOptions] = useState<string[]>([]);
    const [uniqueModelNames, setUniqueModelNames] = useState<string[]>([]);
    const [modelColorMapping, setModelColorMapping] = useState<{ [key: string]: string }>({}); // State for color mapping    
    const [maxCutoff, setMaxCutoff] = useState(100.0);
    const [minCutoff, setMinCutoff] = useState(0.0);
    const [hiddenModels] = useState<string[]>([]); // Track hidden models for onclick chart behavior

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
            const queryParams = new URLSearchParams(window.location.search)
            const response = await fetch(buildV1Url(`datasets/performances/?${queryParams.toString()}`));
            let fetchedData = await response.json();
            fetchedData = convertToCamelCase(fetchedData['model_performance_metric']);
            setFetchedData(fetchedData);
            console.log(fetchedData)
            // Extract the first metric key as the default yAxisMetric
            const initialMetric = Object.keys(fetchedData)[0];
            setYAxisMetric(initialMetric);
            setYAxisMetricOptions(Object.keys(fetchedData));
            //set color mapping
            const uniqueModelNames = Array.from(
                new Set<string>((fetchedData[initialMetric] ?? []).map((item: PerformanceData) => item.modelName))
            );
            const colorPalette = generateColorPalette(uniqueModelNames.length);
            setUniqueModelNames(uniqueModelNames)
            // Create a mapping from model name to a color
            const modelColorMapping: {[key: string]: string} = uniqueModelNames.reduce<{[key: string]: string}>((acc, modelName, index) => {
                acc[modelName] = colorPalette[index % colorPalette.length];
                return acc;
            }, {});
            setModelColorMapping(modelColorMapping);
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    };
    const generateColorPalette = (numColors: number): string[] => {
        const colors = [];
        for (let i = 0; i < numColors; i++) {
            const hue = (i * 360 / numColors) % 360; // Distribute hues evenly
            colors.push(`hsl(${hue}, 70%, 50%)`); // HSL with 70% saturation and 50% lightness
        }
        return colors;
    };

    const calculateVariance = (values: number[]): number => {
        const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
        const variance = values.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / values.length;
        return variance;
    };

    const drawChart = async () => {
        if (!fetchedData || !fetchedData[yAxisMetric]) {
            return;
        }
        setIsLoading(true);
        try {
            const filteredData = fetchedData[yAxisMetric].filter(
                item => item.modelPerformanceValue >= performanceCutoff && !hiddenModels.includes(item.modelName)
            ) as PerformanceData[];
            const chartData = {
                labels: filteredData.map(item => item.datasetName),
                datasets: [{
                    label: yAxisMetric.charAt(0).toUpperCase() + yAxisMetric.slice(1),
                    data: filteredData.map(item => item.modelPerformanceValue),
                    modelNames: filteredData.map(item => item.modelName), 
                    modelTypes: filteredData.map(item => item.modelType), 
                    rawDatas: filteredData.map(item => item.rawData), 
                    backgroundColor: filteredData.map(item => modelColorMapping[item.modelName]), // Use dynamic color
                    borderColor: filteredData.map(item => modelColorMapping[item.modelName]), // Same color for border
                    borderWidth: 1,
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
                    legend: { 
                        display: true,
                        labels: {
                            generateLabels: (_chart: any) => {
                                return uniqueModelNames.map(modelName => {
                                    
                                    // Find the corresponding modelType for the modelName
                                    const modelItem = filteredData.find(item => item.modelName === modelName);
                                    const modelType = modelItem ? modelItem.modelType : '';
            
                                    return {
                                        text: `${modelName}\n(${modelType})`,  // Display modelName with modelType below
                                        fillStyle: modelColorMapping[modelName], // Use the same color mapping
                                        hidden: false,
                                    };
                                });
                            }
                        }
                    },
                                  tooltip: {
                    callbacks: {
                        // Customize tooltip to show both rawData and modelPerformanceValue
                        label: (context: any) => {
                            const rawData = context.dataset.rawDatas[context.dataIndex];
                            const performance = context.raw;
                            const performanceType = context.dataset.label;
                            return [
                                `${performanceType}: ${performance}`,
                                `Raw Data: ${rawData}`
                            ];
                        }
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
                },
                x: {
                    barPercentage: 0.5,   // Adjust bar width 
                    categoryPercentage: 1 // Adjust overall category width
                }
            }
        };
            setOptions(chartOptions);
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    };

    const groupDataBy = (data: any[], groupBy: string): { [key: string]: any[] } => {
        return data.reduce((acc: { [key: string]: any[] }, item: any) => {
            const groupKey = item[groupBy]; // dynamic group key based on groupBy
            if (!acc[groupKey]) {
                acc[groupKey] = [];
            }
            acc[groupKey].push(item);
            return acc;
        }, {});
    };
    
    const sortChartData = (chartData: any, orderBy: string, groupBy: string) => {
        // Access both data and model names in the dataset
        const data = chartData.datasets[0].data as number[];
        const modelNames = chartData.datasets[0].modelNames as string[];
        const modelTypes = chartData.datasets[0].modelTypes as string[];
        const rawDatas = chartData.datasets[0].rawDatas as string[];

        // Create a combined array with datasetName, modelPerformanceValue,  modelName and modelType
        const combinedData = data.map((item, index) => ({
            datasetName: chartData.labels[index],
            modelPerformanceValue: item,
            modelName: modelNames[index],
            modelType: modelTypes[index],
            rawData: rawDatas[index],
        }));
    
        // Group data by the selected `groupBy` field 
        const groupedData = groupDataBy(combinedData, groupBy);
    
        // Flatten the grouped data for sorting and further processing
        let sortedData: any[] = [];
    
        for (const groupKey in groupedData) {
            let group = groupedData[groupKey];
            // Sort the group by modelPerformanceValue (either ascending or descending)
            group.sort((a, b) => {
                if (orderBy === 'Ascending') {
                    return a.modelPerformanceValue - b.modelPerformanceValue;
                } else {
                    return b.modelPerformanceValue - a.modelPerformanceValue;
                }
            });
            sortedData = sortedData.concat(group);
        }
    
        // Update labels, data, and modelNames in the chartData object after sorting
        chartData.labels = sortedData.map(item => item.datasetName);
        chartData.datasets[0].data = sortedData.map(item => item.modelPerformanceValue);
        chartData.datasets[0].rawDatas = sortedData.map(item => item.rawData);
        chartData.datasets[0].ModelNames = sortedData.map(item => item.modelName);
        chartData.datasets[0].modelTypes = sortedData.map(item => item.modelType);
        chartData.datasets[0].backgroundColor = sortedData.map(item => modelColorMapping[item.modelName]);
        chartData.datasets[0].borderColor = sortedData.map(item => modelColorMapping[item.modelName]);
    
        return chartData;
    };
    

    const updateCutoffValues = () => {
        if (!fetchedData || !fetchedData[yAxisMetric]) {
            return;
        }
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

    useEffect(() => {
        handleLoadDataset(); // Automatically trigger on page load
    }, []); 

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
                                <option value="default">Model Performance</option> // sets the default sort to model performance value
                                <option value="rawData">Raw Data</option>
                                <option value="datasetName">Dataset Name</option>
                                <option value="modelName">Model Name</option>
                                <option value="modelType">Model Type</option>
                            </select>
                        </label>
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
