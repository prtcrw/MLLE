import React, {useEffect, useState} from 'react';
import {BrowserRouter as Router, Route, Routes} from 'react-router-dom';
import {useMediaQuery} from 'react-responsive'; // Import useMediaQuery

import Menu from './components/Menu';
import Header from './components/Header.tsx';
import Home from './pages/Home';
import PipelineEditor from './pages/editor/PipelineEditor.tsx';
import FindModels from './pages/analyzer/FindModels.tsx';
import FindPipelines from './pages/analyzer/FindPipelines.tsx';
import FindDatasets from './pages/analyzer/FindDatasets.tsx';
import PlotPerformance from './pages/analyzer/PlotPerformance.tsx';
import AnalyzeModelOutput from './pages/analyzer/AnalyzeModelOutput.tsx';
import AnalyzeDeployedModel from './pages/analyzer/AnalyzeDeployedModel.tsx';
import ComparePipelines from './pages/analyzer/ComparePipelines.tsx';

const Dashboard: React.FC = () => {
    const [isMenuOpen, setIsMenuOpen] = useState(true);
    const isMobile = useMediaQuery({query: '(max-width: 768px)'}); // Check for mobile size

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    return (
        <Router>
            <div className="dashboard">
                <Menu isMenuOpen={isMenuOpen} toggleMenu={toggleMenu} isMobile={isMobile}/>
                <div className={`dashboard-content ${
                    isMenuOpen && isMobile ? 'blurred' : ''}`}>
                    <Header isMenuOpen={isMenuOpen} toggleMenu={toggleMenu}/>
                    <Routes>
                        <Route path="/" element={<Home/>}/>
                        <Route path="/models" element={<FindModels/>}/>
                        <Route path="/models/analyze-deployed-model" element={<AnalyzeDeployedModel/>}/>
                        <Route path="/pipelines" element={<FindPipelines/>}/>
                        <Route path="/pipelines/compare-pipelines" element={<ComparePipelines/>}/>
                        <Route path="/pipelines/edit-pipeline" element={<PipelineEditor/>}/>
                        <Route path="/datasets" element={<FindDatasets/>}/>
                        <Route path="/datasets/plot-performance" element={<PlotPerformance/>}/>
                        <Route path="/datasets/analyze-model-output" element={<AnalyzeModelOutput/>}/>
                    </Routes>
                </div>
            </div>
        </Router>
    );
};

export default Dashboard;
