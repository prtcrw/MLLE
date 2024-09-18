import React from 'react';
import {Scatter} from 'react-chartjs-2';
import {CategoryScale, Chart, Legend, LinearScale, PointElement, Title, Tooltip} from 'chart.js';

// Register Chart.js components
Chart.register(CategoryScale, LinearScale, PointElement, Title, Tooltip, Legend);

// Define static colors for background and borders
const staticColors = [
    { backgroundColor: 'rgba(255, 99, 132, 0.7)', borderColor: 'rgba(255, 99, 132, 1)' }, // Red
    { backgroundColor: 'rgba(54, 162, 235, 0.7)', borderColor: 'rgba(54, 162, 235, 1)' }, // Blue
    { backgroundColor: 'rgba(75, 192, 192, 0.7)', borderColor: 'rgba(75, 192, 192, 1)' }, // Green
    { backgroundColor: 'rgba(255, 206, 86, 0.7)', borderColor: 'rgba(255, 206, 86, 1)' }, // Yellow
    { backgroundColor: 'rgba(153, 102, 255, 0.7)', borderColor: 'rgba(153, 102, 255, 1)' }, // Purple
    { backgroundColor: 'rgba(255, 159, 64, 0.7)', borderColor: 'rgba(255, 159, 64, 1)' },  // Orange
];

const PCAChart: React.FC<{results: any}> = ({results}) => {
    // Return nothing if results doesn't have either metadata or data
    if (!results?.metadata || !results?.data) {
        return null;
    }

    const metadata = results.metadata;
    const data = results.data;

    // Prepare the data for the scatter plot
    const chartData = {
        datasets: metadata.labels.map((label: string, index: number) => {
            // Get the color based on the index, cycling through the array if necessary
            const colorIndex = index % staticColors.length;
            const { backgroundColor, borderColor } = staticColors[colorIndex];

            return {
                label,
                data: data.filter((point: any) => point.label === label).map((point: any) => ({
                    x: point.x,
                    y: point.y
                })),
                backgroundColor,
                borderColor,
                borderWidth: 1,
            };
        })
    };

    return (
        <Scatter data={chartData}/>
    );
};

export default PCAChart;
