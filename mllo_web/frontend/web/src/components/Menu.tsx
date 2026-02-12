import React, {useEffect, useState} from 'react';
import './styles/menu.css'
import Submenu from './Submenu.tsx';
import {Link, Route} from "react-router-dom";
import PlotPerformance from "pages/analyzer/PlotPerformance.tsx";
import AnalyzeModelOutput from "pages/analyzer/AnalyzeModelOutput.tsx";

const Menu: React.FC<{ isMenuOpen: boolean; toggleMenu: () => void; isMobile: boolean }> = ({
                                                                                                isMenuOpen,
                                                                                                toggleMenu,
                                                                                                isMobile
                                                                                            }) => {
    const [closing, setClosing] = useState(false);

    useEffect(() => {
        if (!isMenuOpen && closing) {
            const timer = setTimeout(() => setClosing(false), 300); // Match the duration of the animation
            return () => clearTimeout(timer);
        }
    }, [isMenuOpen, closing]);

    const handleMenuToggle = () => {
        if (isMenuOpen) {
            setClosing(true);
        }
        toggleMenu();
    };

    const handleSubmenuClick = (event: React.MouseEvent) => {
        event.stopPropagation();
        if (isMobile) {
            toggleMenu();
        }
    };

    const analyzerSubmenuItems = [
        { label: 'Find Pipelines', path: '/pipelines' },
        { label: 'Find Models', path: '/datasets' },
        { label: 'Natural Language Query', path: '/datasets/natural-language-query' },
        { label: 'Find Dataset Usages', path: '/datasets/usages' },
        { label: 'Analyze Deployed Models', path: '/models/analyze-deployed-models' },
        { label: 'Plot Performance', path: '/datasets/plot-performance' },
        { label: 'Analyze Model Output', path: '/datasets/analyze-model-output' }
    ];

    const editorSubmenuItems = [
        { label: 'Pipeline Editor', path: '/pipelines/edit-pipeline' }
    ];

    return (
        <div
            className={`menu-container ${isMenuOpen ? (isMobile ? 'mobile-open' : 'open') : closing ? (isMobile ? 'mobile-closing' : 'closing') : ''}`}>
            <div className="menu-content">
                <div className="menu-header">
                    <Link to='/'>
                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}>
                            <img src={'/logo.png'} width={76} />
                            <h2 className="menu-title">MLLE</h2>
                        </div>
                    </Link>
                    <button onClick={handleMenuToggle} className="close-button">
                        ✕
                    </button>
                </div>
                <h4>Analyzer</h4>
                <ul>
                    <li>
                        <Submenu items={analyzerSubmenuItems} onItemClick={handleSubmenuClick}/>
                    </li>
                </ul>
                <h4>Editor</h4>
                <ul>
                    <li>
                        <Submenu items={editorSubmenuItems} onItemClick={handleSubmenuClick}/>
                    </li>
                </ul>
            </div>
        </div>
    );
};

export default Menu;
