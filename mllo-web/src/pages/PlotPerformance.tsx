import React, { useState } from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const PlotPerformance: React.FC = () => {
    const [plotType, setPlotType] = useState('Bar');
    const [yAxisMetric, setYAxisMetric] = useState('Performance');
    const [performanceCutoff, setPerformanceCutoff] = useState(50);
    const [orderBy, setOrderBy] = useState('Ascending');
    const [groupBy, setGroupBy] = useState('Dataset Name');
    const [data, setData] = useState<any>(null);

    const handlePlot = () => {
        // Example data, replace with actual data fetching and processing
        const exampleData = {
            labels: ['Dataset A', 'Dataset B', 'Dataset C'],
            datasets: [{
                label: yAxisMetric,
                data: [65, 59, 80],
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        };
        setData(exampleData);
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
                <div>
                    <label>
                        Y axis (Performance Metric):
                        <select value={yAxisMetric} onChange={(e) => setYAxisMetric(e.target.value)}>
                            <option value="Accuracy">Accuracy</option>
                            <option value="Precision">Precision</option>
                            <option value="Recall">Recall</option>
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
                            <option value="Dataset Name">Dataset Name</option>
                            <option value="Model Name">Model Name</option>
                            {/* Add more group by options as needed */}
                        </select>
                    </label>
                </div>
                <button onClick={handlePlot}>Plot</button>
            </div>
            <div style={{ width: '65%', padding: '20px' }}>
                <h2>Plot</h2>
                {data && <Bar data={data} options={{ responsive: true, plugins: { legend: { position: 'top' }, tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${context.raw}` } } } }} />}
            </div>
        </div>
    );
};

export default PlotPerformance;
