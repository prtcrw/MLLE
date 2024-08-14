import React from 'react';
import './styles/menu.css'
import Submenu from './Submenu.tsx';
import {Link} from "react-router-dom";

const Menu: React.FC<{ isMenuOpen: boolean; toggleMenu: () => void; isMobile: boolean }> = ({isMenuOpen, toggleMenu, isMobile}) => {
    const handleSubmenuClick = (event: React.MouseEvent) => {
        event.stopPropagation();
        if (isMobile) {
            toggleMenu();
        }
    };

    const editorSubmenuItems = [
        {label: 'Pipeline Editor', path: '/pipelines/edit-pipeline'},
    ];

    const analyzerSubmenuItems = [
        {label: 'Find Models', path: '/models'},
        {label: 'Find Pipelines', path: '/pipelines'},
        {label: 'Find Datasets', path: '/datasets'},
    ];

    return (
        <div className={`menu-container ${isMenuOpen ? (isMobile ? 'mobile-open' : 'open') : ''}`}>
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
