import React from 'react';
import './styles/menu.css'
import Submenu from './Submenu.tsx';
import {Link} from "react-router-dom";

const Menu: React.FC<{ isMenuOpen: boolean; toggleMenu: () => void }> = ({isMenuOpen, toggleMenu}) => {
    const handleSubmenuClick = (event: React.MouseEvent) => {
        event.stopPropagation();
    };

    const editorSubmenuItems = [
        {label: 'Pipeline Editor', path: '/pipeline-editor'},
    ];

    const analyzerSubmenuItems = [
        {label: 'Find Models', path: '/find-models'},
        {label: 'Find Pipelines', path: '/find-pipelines'},
        {label: 'Find Datasets', path: '/find-datasets'},
        {label: 'Plot Performance', path: '/plot-performance'},
        {label: 'Analyze Deployed Models', path: '/analyze-deployed-models'},
        {label: 'Compare Pipelines', path: '/compare-pipelines'}
    ];

    return (
        <div className={`menu-container ${isMenuOpen ? 'open' : ''}`}>
            <div className="menu-content">
                <div className="menu-header">
                    <Link to='/'><h2 className="menu-title">MLLO</h2></Link>
                    <button onClick={toggleMenu} className="close-button">
                        ✕
                    </button>
                </div>
                <h4>Editor</h4>
                <ul>
                    <li>
                        <Submenu items={editorSubmenuItems} onItemClick={handleSubmenuClick}/>
                    </li>
                </ul>
                <h4>Analyzer</h4>
                <ul>
                    <li>
                        <Submenu items={analyzerSubmenuItems} onItemClick={handleSubmenuClick}/>
                    </li>
                </ul>
            </div>
        </div>
    );
};

export default Menu;
