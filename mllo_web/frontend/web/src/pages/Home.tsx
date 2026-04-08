import React, {useEffect, useState} from 'react';
import {Link} from 'react-router-dom';
import {DashboardSummary, getDashboardSummary} from '../services/api';
import './analyzer/styles/home.css';

const quickActions = [
    {
        title: 'Chat with MLLO',
        description: 'Have a conversation about MLLO classes, instances, pipelines, models, and datasets.',
        path: '/chat-with-mllo',
        tone: 'blue',
    },
    {
        title: 'Find Datasets',
        description: 'Search datasets, including standalone records and workflow-linked inputs.',
        path: '/datasets',
        tone: 'teal',
    },
    {
        title: 'Find Pipelines',
        description: 'Trace pipelines by associated models or datasets.',
        path: '/pipelines',
        tone: 'amber',
    },
    {
        title: 'Dataset Usages',
        description: 'Inspect where datasets are consumed across training and evaluation flows.',
        path: '/datasets/usages',
        tone: 'blue',
    },
    {
        title: 'LLM Query',
        description: 'Ask natural-language questions and inspect generated SPARQL and results.',
        path: '/datasets/natural-language-query',
        tone: 'slate',
    },
];

const workflowSteps = [
    'Start with a focused search instead of loading the whole graph.',
    'Refine with type and time filters once the initial result set is clear.',
    'Jump into pipeline comparison, model output analysis, or natural-language querying.',
];

const Home: React.FC = () => {
    const [summary, setSummary] = useState<DashboardSummary | null>(null);
    const [summaryError, setSummaryError] = useState<string | null>(null);

    useEffect(() => {
        const loadSummary = async () => {
            try {
                const response = await getDashboardSummary();
                setSummary(response);
            } catch (error) {
                setSummaryError((error as Error).message);
            }
        };

        void loadSummary();
    }, []);

    const statCards = [
        {label: 'Models', value: summary?.models ?? '...'},
        {label: 'Datasets', value: summary?.datasets ?? '...'},
        {label: 'Pipelines', value: summary?.pipelines ?? '...'},
        {label: 'Deployed Models', value: summary?.deployed_models ?? '...'},
    ];

    return (
        <div className="home-page">
            <section className="home-hero">
                <div className="home-hero-copy">
                    <div className="home-kicker">MLLO Workbench</div>
                    <h1>Explore datasets, models, pipelines, and dataset usage from one place.</h1>
                    <div className="home-hero-actions">
                        <Link className="home-primary-cta" to="/datasets">
                            Open Dataset Search
                        </Link>
                        <Link className="home-secondary-cta" to="/chat-with-mllo">
                            Chat with MLLO
                        </Link>
                    </div>
                </div>

                <div className="home-metrics-card">
                    <div className="home-metrics-title-row">
                        <div>
                            <div className="home-card-eyebrow">Ontology Snapshot</div>
                            <h2>Current graph summary</h2>
                        </div>
                        {summaryError && <span className="home-stats-error">Unavailable</span>}
                    </div>
                    <div className="home-stats-grid">
                        {statCards.map((card) => (
                            <div key={card.label} className="home-stat-card">
                                <span className="home-stat-value">{card.value}</span>
                                <span className="home-stat-label">{card.label}</span>
                            </div>
                        ))}
                    </div>
                    {summaryError && (
                        <p className="home-metrics-note">Could not load ontology counts right now.</p>
                    )}
                </div>
            </section>

            <section className="home-grid">
                <div className="home-panel">
                    <div className="home-panel-header">
                        <h2>Quick Actions</h2>
                        <p>Jump into the main workflows directly from the landing page.</p>
                    </div>
                    <div className="home-action-grid">
                        {quickActions.map((action) => (
                            <Link key={action.title} to={action.path} className={`home-action-card home-tone-${action.tone}`}>
                                <div className="home-action-title-row">
                                    <h3>{action.title}</h3>
                                    <span className="home-action-arrow">↗</span>
                                </div>
                                <p>{action.description}</p>
                            </Link>
                        ))}
                    </div>
                </div>

                <div className="home-panel home-panel-compact">
                    <div className="home-panel-header">
                        <h2>Recommended Flow</h2>
                        <p>A faster path for large repositories.</p>
                    </div>
                    <div className="home-step-list">
                        {workflowSteps.map((step, index) => (
                            <div key={step} className="home-step-item">
                                <div className="home-step-index">0{index + 1}</div>
                                <div className="home-step-text">{step}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

        </div>
    );
};

export default Home;
