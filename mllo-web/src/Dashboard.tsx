import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Menu from './components/Menu';
import Breadcrumb from './components/Breadcrumb';
import Home from './pages/Home';
import ComparePipelines from './pages/ComparePipelines';
import FindModels from './pages/FindModels';
import FindPipelines from './pages/FindPipelines';
import AnalyzeDeployedModels from './pages/AnalyzeDeployedModels';
import FindDatasets from './pages/FindDatasets';
import PlotPerformance from './pages/PlotPerformance';

const Dashboard: React.FC = () => {
    return (
        <Router>
            <div className="dashboard">
                <Menu />
                <div className="dashboard-content">
                    <Breadcrumb />
                    <Routes>
                        <Route path="/" element={<Home />} />
                        <Route path="/compare-pipelines" element={<ComparePipelines />} />
                        <Route path="/find-models" element={<FindModels />} />
                        <Route path="/find-pipelines" element={<FindPipelines />} />
                        <Route path="/analyze-deployed-models" element={<AnalyzeDeployedModels />} />
                        <Route path="/find-datasets" element={<FindDatasets />} />
                        <Route path="/plot-performance" element={<PlotPerformance />} />
                    </Routes>
                </div>
            </div>
        </Router>
    );
};

export default Dashboard;
