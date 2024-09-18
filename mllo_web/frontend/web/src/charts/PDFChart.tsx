import React from 'react';
import { Line } from 'react-chartjs-2';
import { BarElement, CategoryScale, Chart, LinearScale, LineElement, PointElement, Tooltip, Legend } from 'chart.js';

// Register the required chart components
Chart.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip, Legend);

type ResultItem = {
  predicted_label: number;
};

type DatasetResult = {
  dataset: string;
  results: ResultItem[];
};

type PDFChartProps = {
  outputResults: DatasetResult[];
};

const PDFChart: React.FC<PDFChartProps> = ({ outputResults }) => {
    if (!outputResults || outputResults.length === 0) {
        return <div>No data available for PDF</div>;
    }

    const numberOfLabels = 10; // Assuming 10 classes, adjust if necessary

    // Prepare data for each dataset
    const datasets = outputResults.map((datasetResult, index) => {
        const predictedLabels = datasetResult.results.map(result => result.predicted_label);

        // Calculate histogram data (frequencies of predicted classes)
        const labelCounts = Array(numberOfLabels).fill(0);
        predictedLabels.forEach(label => labelCounts[label] += 1);

        // Calculate the probability density function (PDF)
        const pdf = labelCounts.map(count => count / predictedLabels.length);

        // Generate a color based on the index
        const hue = (index * 137) % 360; // Use golden angle approximation for color distribution
        const color = `hsla(${hue}, 70%, 60%, 1)`;

        return {
            label: datasetResult.dataset,
            data: pdf,
            fill: false,
            borderColor: color,
            tension: 0.1,
        };
    });

    // Prepare the chart data
    const chartData = {
        labels: Array.from({ length: numberOfLabels }, (_, i) => `Class ${i}`),
        datasets: datasets,
    };

    const options = {
        responsive: true,
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Predicted Class'
                }
            },
            y: {
                beginAtZero: true,
                title: {
                    display: true,
                    text: 'Probability Density'
                }
            }
        },
        plugins: {
            legend: {
                position: 'top' as const,
            },
        },
    };

    return <Line data={chartData} options={options} />;
};

export default PDFChart;
