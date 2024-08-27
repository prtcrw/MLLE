import React from 'react';
import {Line} from 'react-chartjs-2';
import {BarElement, CategoryScale, Chart, LinearScale, LineElement, PointElement, Tooltip} from 'chart.js';

// Register the required chart components
Chart.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip);


const PDFChart: React.FC<{ results: any }> = ({results}) => {
    if (!results || !Array.isArray(results)) {
        return null;
    }

    // Extract true and predicted labels
    const trueLabels = results.map(result => result.true_label);
    const predictedLabels = results.map(result => result.predicted_label);

    // Calculate histogram data (frequencies of predicted classes)
    const labelCounts = Array(10).fill(0);
    predictedLabels.forEach(label => labelCounts[label] += 1);

    // Calculate the probability density function (PDF)
    const pdf = labelCounts.map(count => count / predictedLabels.length);

    // Prepare data for PDF (line chart)
    const pdfData = {
        labels: Array.from({length: 10}, (_, i) => `Class ${i}`),
        datasets: [
            {
                label: 'Probability Density',
                data: pdf,
                fill: false,
                borderColor: 'rgba(255, 99, 132, 1)',
                tension: 0.1,
            },
        ],
    };

    return (
        <Line data={pdfData}/>
    );
};

export default PDFChart;
