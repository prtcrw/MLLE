import React, {useEffect, useState} from 'react';
import './styles/menu.css'
import Submenu from './Submenu.tsx';
import {Link} from "react-router-dom";

const Menu: React.FC<{ isMenuOpen: boolean; toggleMenu: () => void; isMobile: boolean }> = ({isMenuOpen, toggleMenu, isMobile}) => {
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

    const editorSubmenuItems = [
        {label: 'Pipeline Editor', path: '/pipelines/edit-pipeline'},
    ];

    const analyzerSubmenuItems = [
        {label: 'Find Models', path: '/models'},
        {label: 'Analyze Deployed Models', path: '/models/analyze-deployed-models'},
        {label: 'Find Pipelines', path: '/pipelines'},
        {label: 'Find Datasets', path: '/datasets'},
    ];

    return (
        <div className={`menu-container ${isMenuOpen ? (isMobile ? 'mobile-open' : 'open') : closing ? (isMobile ? 'mobile-closing' : 'closing') : ''}`}>
            <div className="menu-content">
                <div className="menu-header">
                    <Link to='/'><h2 className="menu-title">MLLO</h2></Link>
                    <button onClick={handleMenuToggle} className="close-button">
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
