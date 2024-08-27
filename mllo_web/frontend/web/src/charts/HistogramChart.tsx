import React from 'react';
import {Bar} from 'react-chartjs-2';
import {BarElement, CategoryScale, Chart, LinearScale, LineElement, PointElement, Tooltip} from 'chart.js';

// Register the required chart components
Chart.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip);


const HistogramChart: React.FC<{ results: any }> = ({results}) => {
    if (!results || !Array.isArray(results)) {
        return null;
    }

    // Extract true and predicted labels
    const trueLabels = results.map(result => result.true_label);
    const predictedLabels = results.map(result => result.predicted_label);

    // Calculate histogram data (frequencies of predicted classes)
    const labelCounts = Array(10).fill(0);
    predictedLabels.forEach(label => labelCounts[label] += 1);

    // Prepare data for histogram (bar chart)
    const histogramData = {
        labels: Array.from({length: 10}, (_, i) => `Class ${i}`),
        datasets: [
            {
                label: 'Predicted Frequency',
                data: labelCounts,
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
            },
        ],
    };

    return (
        <Bar data={histogramData}/>
    );
};

export default HistogramChart;
