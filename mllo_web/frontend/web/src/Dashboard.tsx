import React, {useState} from 'react';
import {BrowserRouter as Router, Navigate, Route, Routes} from 'react-router-dom';
import {useMediaQuery} from 'react-responsive'; // Import useMediaQuery
import Menu from './components/Menu';
import Header from './components/Header.tsx';
import DemoReplay from './components/DemoReplay.tsx';
import Home from './pages/Home';
import PipelineEditor from './pages/editor/PipelineEditor.tsx';
import FindDatasetUsages from './pages/analyzer/FindDatasetUsages.tsx';
import FindPipelines from './pages/analyzer/FindPipelines.tsx';
import FindDatasets from './pages/analyzer/FindDatasets.tsx';
import FindModels from './pages/analyzer/FindModels.tsx';
import NaturalLanguageQuery from './pages/analyzer/NaturalLanguageQuery.tsx';
import ChatWithMLLO from './pages/analyzer/ChatWithMLLO.tsx';
import NLQSettings, {
    SettingsGraphDbPage,
    SettingsLlmPage,
    SettingsLogsPage,
    SettingsOverview
} from './pages/analyzer/NLQSettings.tsx';
import PlotPerformance from './pages/analyzer/PlotPerformance.tsx';
import AnalyzeModelOutput from './pages/analyzer/AnalyzeModelOutput.tsx';
import AnalyzeDeployedModels from './pages/analyzer/AnalyzeDeployedModels.tsx';
import ComparePipelines from './pages/analyzer/ComparePipelines.tsx';
import DemoAutomationHome from './pages/demo/DemoAutomationHome.tsx';

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
                <div className={`dashboard-content ${isMenuOpen && !isMobile ? 'slide-out' : 'slide-in'} ${isMenuOpen && isMobile ? 'blurred' : ''}`}>
                    <Header isMenuOpen={isMenuOpen} toggleMenu={toggleMenu}/>
                    <Routes>
                        <Route path="/" element={<Home/>}/>
                        <Route path="/demos" element={<DemoAutomationHome/>}/>
                        <Route path="/chat-with-mllo" element={<ChatWithMLLO/>}/>
                        <Route path="/datasets/natural-language-query" element={<NaturalLanguageQuery/>}/>
                        <Route path="/settings/*" element={<NLQSettings/>}>
                            <Route index element={<SettingsOverview/>}/>
                            <Route path="llm" element={<SettingsLlmPage/>}/>
                            <Route path="graphdb" element={<SettingsGraphDbPage/>}/>
                            <Route path="logs" element={<SettingsLogsPage/>}/>
                            <Route path="*" element={<Navigate to="/settings/llm" replace/>}/>
                        </Route>
                        <Route path="/models/analyze-models" element={<AnalyzeDeployedModels/>}/>
                        <Route path="/models/analyze-deployed-models" element={<AnalyzeDeployedModels/>}/>
                        <Route path="/models" element={<FindModels/>}/>
                        <Route path="/pipelines" element={<FindPipelines/>}/>
                        <Route path="/pipelines/compare-pipelines" element={<ComparePipelines/>}/>
                        <Route path="/pipelines/edit-pipeline" element={<PipelineEditor/>}/>
                        <Route path="/datasets" element={<FindDatasets/>}/>
                        <Route path="/datasets/usages" element={<FindDatasetUsages/>}/>
                        <Route path="/datasets/plot-performance" element={<PlotPerformance/>}/>
                        <Route path="/datasets/analyze-model-output" element={<AnalyzeModelOutput/>}/>
                    </Routes>
                    <DemoReplay/>
                </div>
            </div>
        </Router>
    );
};

export default Dashboard;
