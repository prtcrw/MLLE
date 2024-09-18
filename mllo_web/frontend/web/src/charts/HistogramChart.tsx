import React from 'react';
import { Bar } from 'react-chartjs-2';
import { 
  BarElement, 
  CategoryScale, 
  Chart as ChartJS, 
  LinearScale, 
  LineElement, 
  PointElement, 
  Tooltip,
  Legend
} from 'chart.js';

// Register the required chart components
ChartJS.register(
  CategoryScale, 
  LinearScale, 
  BarElement, 
  PointElement, 
  LineElement, 
  Tooltip,
  Legend
);

// Define types for the expected data structure
type ResultItem = {
  true_label: number;
  predicted_label: number;
};

type DatasetResult = {
  dataset: string;
  results: ResultItem[];
};

type HistogramChartProps = {
  outputResults: DatasetResult[];
};

const HistogramChart: React.FC<HistogramChartProps> = ({ outputResults }) => {
    if (!outputResults || outputResults.length === 0) {
        return <div>No data available for histogram</div>;
    }

    const numberOfLabels = 10; // Assuming 10 classes, adjust if necessary

    // Prepare data for bar chart (side by side columns)
    const datasets = outputResults.map((datasetResult, index) => {
        const labelCounts = Array(numberOfLabels).fill(0);
        datasetResult.results.forEach(item => {
            if (item.predicted_label >= 0 && item.predicted_label < numberOfLabels) {
                labelCounts[item.predicted_label]++;
            }
        });

        // Generate a color based on the index
        const hue = (index * 137) % 360; // Use golden angle approximation for color distribution
        const color = `hsla(${hue}, 70%, 60%, 0.6)`;

        return {
            label: datasetResult.dataset,
            data: labelCounts,
            backgroundColor: color,
        };
    });

    const chartData = {
        labels: Array.from({ length: numberOfLabels }, (_, i) => `Class ${i}`),
        datasets: datasets,
    };

    const options = {
        responsive: true,
        scales: {
            x: {
                stacked: false, // Disable stacking for side-by-side bars
                title: {
                    display: true,
                    text: 'Predicted Class'
                }
            },
            y: {
                stacked: false, // Disable stacking for side-by-side bars
                beginAtZero: true,
                title: {
                    display: true,
                    text: 'Frequency'
                }
            }
        },
        plugins: {
            legend: {
                position: 'top' as const,
            }
        },
    };

    return <Bar data={chartData} options={options} />;
};

export default HistogramChart;
