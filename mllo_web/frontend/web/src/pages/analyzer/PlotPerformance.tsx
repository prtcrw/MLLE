import React, { useState } from 'react';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import { Bar, Line } from 'react-chartjs-2';
import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, LineElement, PointElement, Title, Tooltip } from 'chart.js';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend);

interface PerformanceData {
    datasetName: string;
    accuracy: number;
    precision: number;
    recall: number;
}

const PlotPerformance: React.FC = () => {
    const [plotType, setPlotType] = useState('Bar');
    const [yAxisMetric, setYAxisMetric] = useState('accuracy');
    const [performanceCutoff, setPerformanceCutoff] = useState(50);
    const [orderBy, setOrderBy] = useState('Ascending');
    const [groupBy, setGroupBy] = useState('datasetName');
    const [isLoading, setIsLoading] = useState(false);
    const [data, setData] = useState<any>(null);

    const handlePlot = async () => {
        setIsLoading(true); // Set loading to true
        try {
            // Fetch data with filters
            const response = await fetch(buildV1Url(`performances/?yAxisMetric=${yAxisMetric}&performanceCutoff=${performanceCutoff}&orderBy=${orderBy}&groupBy=${groupBy}`));
            const fetchedData: PerformanceData[] = await response.json();

            // Prepare the chart data
            const chartData = {
                labels: fetchedData.map(item => item[groupBy as keyof PerformanceData]),
                datasets: [{
                    label: yAxisMetric.charAt(0).toUpperCase() + yAxisMetric.slice(1), // Capitalize the label
                    data: fetchedData.map(item => item[yAxisMetric as keyof PerformanceData]),
                    backgroundColor: plotType === 'Bar' ? 'rgba(75, 192, 192, 0.2)' : 'rgba(153, 102, 255, 0.2)',
                    borderColor: plotType === 'Bar' ? 'rgba(75, 192, 192, 1)' : 'rgba(153, 102, 255, 1)',
                    borderWidth: 1,
                    fill: plotType === 'Line', // Fill the area under the line only if it's a Line chart
                }]
            };
            setData(chartData);
        } finally {
            setIsLoading(false); // Set loading to false after fetching
        }
    };

    return (
        <>
            {isLoading && <LoadingBar isLoading={isLoading}/>}
            <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <div style={{width: '30%'}}>
                    <h2>Filters</h2>
                    <div>
                        <label>
                            Plot Type:
                            <select value={plotType} onChange={(e) => setPlotType(e.target.value)}>
                                <option value="Bar">Bar</option>
                                <option value="Line">Line</option>
                                {/* Add more plot types as needed */}
                            </select>
                        </label>
                    </div>
                    <div>
                        <label>
                            Y axis (Performance Metric):
                            <select value={yAxisMetric} onChange={(e) => setYAxisMetric(e.target.value)}>
                                <option value="accuracy">Accuracy</option>
                                <option value="precision">Precision</option>
                                <option value="recall">Recall</option>
                                {/* Add more metrics as needed */}
                            </select>
                        </label>
                    </div>
                    <div>
                        <label>
                            Performance Cutoff:
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={performanceCutoff}
                                onChange={(e) => setPerformanceCutoff(Number(e.target.value))}
                            />
                            <span>{performanceCutoff}</span>
                        </label>
                    </div>
                    <div>
                        <label>
                            Order By:
                            <select value={orderBy} onChange={(e) => setOrderBy(e.target.value)}>
                                <option value="Ascending">Ascending</option>
                                <option value="Descending">Descending</option>
                            </select>
                        </label>
                    </div>
                    <div>
                        <label>
                            Group By:
                            <select value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
                                <option value="datasetName">Dataset Name</option>
                                <option value="modelName">Model Name</option>
                                {/* Add more group by options as needed */}
                            </select>
                        </label>
                    </div>
                    <button onClick={handlePlot}>Plot</button>
                </div>
                <div style={{width: '65%'}}>
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
