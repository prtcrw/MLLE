import React from 'react';
import {Scatter} from 'react-chartjs-2';
import {CategoryScale, Chart, Legend, LinearScale, PointElement, Title, Tooltip} from 'chart.js';

// Register Chart.js components
Chart.register(CategoryScale, LinearScale, PointElement, Title, Tooltip, Legend);


const PCAChart: React.FC<{results: any}> = ({results}) => {
    // Return nothing if results doesn't have either metadata or data
    if (!results?.metadata || !results?.data) {
        return null;
    }

    const metadata = results.metadata;
    const data = results.data;

    // Prepare the data for the scatter plot
    const chartData = {
        datasets: metadata.labels.map((label: string) => ({
            label,
            data: data.filter((point: any) => point.label === label).map((point: any) => ({
                x: point.x,
                y: point.y
            })),
            backgroundColor: `rgba(${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, 0.7)`,
            borderColor: `rgba(${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, 1)`,
            borderWidth: 1,
        }))
    };

    return (
        <Scatter data={chartData}/>
    );
};

export default PCAChart;
