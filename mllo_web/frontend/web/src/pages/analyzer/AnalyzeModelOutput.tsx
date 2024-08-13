import React, { useState } from 'react';
import {buildV1Url} from '../../services/api';
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

const AnalyzeModelOutput: React.FC = () => {
    const [plotType, setPlotType] = useState('Bar');
    const [yAxisMetric, setYAxisMetric] = useState('accuracy');
    const [performanceCutoff, setPerformanceCutoff] = useState(50);
    const [orderBy, setOrderBy] = useState('Ascending');
    const [groupBy, setGroupBy] = useState('datasetName');
    const [data, setData] = useState<any>(null);

    const handlePlot = async () => {
        // Fetch data with filters
        const response = await fetch(buildV1Url(`performances/`));
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
    };

    return (
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div style={{ width: '30%', padding: '20px' }}>
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
                <button onClick={handlePlot}>Plot</button>
            </div>
            <div style={{ width: '65%', padding: '20px' }}>
                <h2>Plot</h2>
                {data && (
                    plotType === 'Bar' ? (
                        <Bar data={data} options={{
                            responsive: true,
                            plugins: {
                                legend: { position: 'top' },
                                tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${context.raw}` } }
                            }
                        }} />
                    ) : (
                        <Line data={data} options={{
                            responsive: true,
                            plugins: {
                                legend: { position: 'top' },
                                tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${context.raw}` } }
                            }
                        }} />
                    )
                )}
            </div>
        </div>
    );
};

export default AnalyzeModelOutput;
