import React from 'react';
import {Link} from 'react-router-dom';
import './styles/demo_automation_home.css';

const demos = [
    {
        title: 'MNIST MLLO Evidence Walkthrough',
        href: '/?replay=mnist',
        description: 'Automates real MLLE pages with visible cursor movement, typed searches, scrolling, linked evidence navigation, and Chat with MLLO.',
        duration: '6-7 min',
        steps: ['Home', 'Models', 'Dataset Usages', 'Pipelines', 'Chat'],
    },
    {
        title: 'Handwritten Digit Model Selection',
        href: '/?replay=model-selection',
        description: 'Automates a data scientist flow for selecting an MNIST classification model, tracing evidence, then previewing a preprocessing pipeline in the editor and Chat with MLLO.',
        duration: '7-9 min',
        steps: ['Models', 'Performance', 'Datasets', 'Pipelines', 'Editor', 'Chat'],
    },
];

const DemoAutomationHome: React.FC = () => {
    return (
        <main className="demo-automation-page">
            <section className="demo-automation-hero">
                <div>
                    <span>Demo Automation</span>
                    <h1>Replayable MLLE Screen-Capture Walkthroughs</h1>
                    <p>Launch real app automations with pause, stop, and section seeking for recording.</p>
                </div>
            </section>

            <section className="demo-automation-list" aria-label="Available demo automations">
                {demos.map((demo) => (
                    <article key={demo.href} className="demo-automation-card">
                        <div>
                            <span>{demo.duration}</span>
                            <h2>{demo.title}</h2>
                            <p>{demo.description}</p>
                            <div className="demo-automation-steps">
                                {demo.steps.map((step) => (
                                    <span key={step}>{step}</span>
                                ))}
                            </div>
                        </div>
                        <Link to={demo.href}>Run Replay</Link>
                    </article>
                ))}
            </section>
        </main>
    );
};

export default DemoAutomationHome;
