import React, {useEffect, useState} from 'react';
import {Link, NavLink} from 'react-router-dom';
import './styles/menu.css';

const navGroups = [
    {
        heading: 'Conversation',
        eyebrow: 'Ask and Inspect',
        items: [
            {label: 'Chat with MLLO', path: '/chat-with-mllo'},
            {label: 'Natural Language Query', path: '/datasets/natural-language-query'},
        ],
    },
    {
        heading: 'Discovery',
        eyebrow: 'Search and Compare',
        items: [
            {label: 'Find Datasets', path: '/datasets'},
            {label: 'Find Pipelines', path: '/pipelines'},
            {label: 'Find Dataset Usages', path: '/datasets/usages'},
            {label: 'Analyze Deployed Models', path: '/models/analyze-deployed-models'},
        ],
    },
    {
        heading: 'Visualization',
        eyebrow: 'Explore Outputs',
        items: [
            {label: 'Plot Performance', path: '/datasets/plot-performance'},
            {label: 'Analyze Model Output', path: '/datasets/analyze-model-output'},
        ],
    },
    {
        heading: 'Build',
        eyebrow: 'Editor',
        items: [
            {label: 'Pipeline Editor', path: '/pipelines/edit-pipeline'},
        ],
    },
];

const Menu: React.FC<{ isMenuOpen: boolean; toggleMenu: () => void; isMobile: boolean }> = ({
    isMenuOpen,
    toggleMenu,
    isMobile
}) => {
    const [closing, setClosing] = useState(false);

    useEffect(() => {
        if (!isMenuOpen && closing) {
            const timer = setTimeout(() => setClosing(false), 300);
            return () => clearTimeout(timer);
        }
    }, [isMenuOpen, closing]);

    const handleMenuToggle = () => {
        if (isMenuOpen) {
            setClosing(true);
        }
        toggleMenu();
    };

    const handleNavClick = () => {
        if (isMobile) {
            toggleMenu();
        }
    };

    return (
        <div
            className={`menu-container ${isMenuOpen ? (isMobile ? 'mobile-open' : 'open') : closing ? (isMobile ? 'mobile-closing' : 'closing') : ''}`}
        >
            <div className="menu-content">
                <div className="menu-header">
                    <Link to="/" className="menu-brand" onClick={isMobile ? toggleMenu : undefined}>
                        <img src="/logo.png" width={60} alt="MLLE"/>
                        <div className="menu-brand-copy">
                            <span className="menu-brand-kicker">Workbench</span>
                            <h2 className="menu-title">MLLE</h2>
                        </div>
                    </Link>
                    <button onClick={handleMenuToggle} className="close-button" aria-label="Close menu">
                        ✕
                    </button>
                </div>

                <Link to="/" className="menu-home-link" onClick={isMobile ? toggleMenu : undefined}>
                    Overview
                </Link>

                <div className="menu-groups">
                    {navGroups.map((group) => (
                        <section key={group.heading} className="menu-group">
                            <div className="menu-group-heading">
                                <span>{group.eyebrow}</span>
                                <h4>{group.heading}</h4>
                            </div>
                            <nav className="menu-group-links" aria-label={group.heading}>
                                {group.items.map((item) => (
                                    <NavLink
                                        key={item.path}
                                        to={item.path}
                                        end
                                        onClick={handleNavClick}
                                        className={({isActive}) => `menu-link-card${isActive ? ' is-active' : ''}`}
                                    >
                                        <strong>{item.label}</strong>
                                    </NavLink>
                                ))}
                            </nav>
                        </section>
                    ))}
                </div>

                <div className="menu-footer">
                    <NavLink
                        to="/settings"
                        end
                        className={({isActive}) => `menu-settings-link${isActive ? ' is-active' : ''}`}
                        onClick={isMobile ? toggleMenu : undefined}
                    >
                        Settings
                    </NavLink>
                </div>
            </div>
        </div>
    );
};

export default Menu;
