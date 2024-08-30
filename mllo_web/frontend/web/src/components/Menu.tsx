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

    const modelSubmenuItems = [
        { label: 'Analyze Deployed Models', path: '/models/analyze-deployed-models' },
    ];

    const pipelineSubmenuItems = [
        {
            label: 'Find Pipelines', path: '/pipelines',
            children: [
                {label: 'Pipeline Editor', path: '/pipelines/edit-pipeline'},
            ]
        },
    ];

    const datasetSubmenuItems = [
        {
            label: 'Find Datasets', path: '/datasets',
            children: [
                {label: 'Plot Performance', path: '/datasets/plot-performance'},
                {label: 'Analyze Model Output', path: '/datasets/analyze-model-output'},
            ]
        },
        {label: 'Find Dataset Usages', path: '/datasets/usages'}
    ];

    return (
        <div
            className={`menu-container ${isMenuOpen ? (isMobile ? 'mobile-open' : 'open') : closing ? (isMobile ? 'mobile-closing' : 'closing') : ''}`}>
            <div className="menu-content">
                <div className="menu-header">
                    <Link to='/'><h2 className="menu-title">MLLO</h2></Link>
                    <button onClick={handleMenuToggle} className="close-button">
                        ✕
                    </button>
                </div>
                <h4>Model</h4>
                <ul>
                    <li>
                        <Submenu items={modelSubmenuItems} onItemClick={handleSubmenuClick}/>
                    </li>
                </ul>
                <h4>Pipeline</h4>
                <ul>
                    <li>
                        <Submenu items={pipelineSubmenuItems} onItemClick={handleSubmenuClick}/>
                    </li>
                </ul>
                <h4>Dataset</h4>
                <ul>
                    <li>
                        <Submenu items={datasetSubmenuItems} onItemClick={handleSubmenuClick}/>
                    </li>
                </ul>
            </div>
        </div>
    );
};

export default Menu;
