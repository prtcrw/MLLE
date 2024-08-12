import React, {useState} from 'react';
import {MemoryRouter as Router, Route, Routes} from 'react-router-dom';
import Menu from './components/Menu';
import Header from './components/Header.tsx';
import Home from './pages/Home';
import PipelineEditor from './pages/editor/PipelineEditor.tsx';
import FindModels from './pages/analyzer/FindModels.tsx';
import FindPipelines from './pages/analyzer/FindPipelines.tsx';
import FindDatasets from './pages/analyzer/FindDatasets.tsx';
import PlotPerformance from './pages/analyzer/PlotPerformance.tsx';
import AnalyzeDeployedModels from './pages/analyzer/AnalyzeDeployedModels.tsx';
import ComparePipelines from './pages/analyzer/ComparePipelines.tsx';

const Dashboard: React.FC = () => {
    const [isMenuOpen, setIsMenuOpen] = useState(true);

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    return (
        <Router>
            <div className="dashboard">
                <Menu isMenuOpen={isMenuOpen} toggleMenu={toggleMenu} />
                <div className="dashboard-content">
                    <Header isMenuOpen={isMenuOpen} toggleMenu={toggleMenu} />
                    <Routes>
                        <Route path="/" element={<Home />} />
                        <Route path="/pipeline-editor" element={<PipelineEditor />} />
                        <Route path="/find-models" element={<FindModels />} />
                        <Route path="/find-pipelines" element={<FindPipelines />} />
                        <Route path="/find-datasets" element={<FindDatasets />} />
                        <Route path="/plot-performance" element={<PlotPerformance />} />
                        <Route path="/analyze-deployed-models" element={<AnalyzeDeployedModels />} />
                        <Route path="/compare-pipelines" element={<ComparePipelines />} />
                    </Routes>
                </div>
            </div>
        </Router>
    );
};

export default Dashboard;
