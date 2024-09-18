import React from 'react';
import { Scatter } from 'react-chartjs-2';
import { CategoryScale, Chart, Legend, LinearScale, PointElement, Title, Tooltip } from 'chart.js';

// Register Chart.js components
Chart.register(CategoryScale, LinearScale, PointElement, Title, Tooltip, Legend);

const PCAChart: React.FC<{ results: any }> = ({ results }) => {
    // Return nothing if results doesn't have either metadata or data
    if (!results?.metadata || !results?.data) {
        return null;
    }

    const metadata = results.metadata;
    const data = results.data;

    // Define static colors for the datasets (10 distinct colors)
    const staticColors = [
        { backgroundColor: 'rgba(75, 192, 192, 0.7)', borderColor: 'rgba(75, 192, 192, 1)' }, // Color 1
        { backgroundColor: 'rgba(255, 99, 132, 0.7)', borderColor: 'rgba(255, 99, 132, 1)' }, // Color 2
        { backgroundColor: 'rgba(54, 162, 235, 0.7)', borderColor: 'rgba(54, 162, 235, 1)' }, // Color 3
        { backgroundColor: 'rgba(255, 206, 86, 0.7)', borderColor: 'rgba(255, 206, 86, 1)' }, // Color 4
        { backgroundColor: 'rgba(153, 102, 255, 0.7)', borderColor: 'rgba(153, 102, 255, 1)' }, // Color 5
        { backgroundColor: 'rgba(255, 159, 64, 0.7)', borderColor: 'rgba(255, 159, 64, 1)' }, // Color 6
        { backgroundColor: 'rgba(0, 128, 0, 0.7)', borderColor: 'rgba(0, 128, 0, 1)' },       // Color 7
        { backgroundColor: 'rgba(128, 0, 128, 0.7)', borderColor: 'rgba(128, 0, 128, 1)' },   // Color 8
        { backgroundColor: 'rgba(255, 69, 0, 0.7)', borderColor: 'rgba(255, 69, 0, 1)' },     // Color 9
        { backgroundColor: 'rgba(70, 130, 180, 0.7)', borderColor: 'rgba(70, 130, 180, 1)' }  // Color 10
    ];

    // Prepare the data for the scatter plot
    const chartData = {
        datasets: metadata.labels.map((label: string, index: number) => ({
            label,
            data: data.filter((point: any) => point.label === label).map((point: any) => ({
                x: point.x,
                y: point.y
            })),
            backgroundColor: staticColors[index % staticColors.length].backgroundColor,
            borderColor: staticColors[index % staticColors.length].borderColor,
            borderWidth: 1,
        }))
    };

    return (
        <Scatter data={chartData} />
    );
};

export default PCAChart;
