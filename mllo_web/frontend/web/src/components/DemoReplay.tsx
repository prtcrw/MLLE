import React, {useEffect, useMemo, useRef, useState} from 'react';
import './styles/demo_replay.css';

interface CursorPosition {
    x: number;
    y: number;
}

interface ReplayStatus {
    step: string;
    detail: string;
}

type WaitTarget = string | (() => boolean);

interface ReplaySection {
    id: string;
    label: string;
    url: string;
}

const replaySectionsByDemo: Record<string, ReplaySection[]> = {
    mnist: [
    {id: 'home', label: 'Home', url: '/?replay=mnist&from=home'},
    {id: 'models', label: 'Models', url: '/models?replay=mnist&from=models'},
    {id: 'datasets', label: 'Dataset Usages', url: '/datasets/usages?replay=mnist&from=datasets&search_term=PreprocessedDataset1'},
    {id: 'pipelines', label: 'Pipelines', url: '/pipelines?replay=mnist&from=pipelines'},
    {id: 'chat', label: 'Chat', url: '/chat-with-mllo?replay=mnist&from=chat'},
    ],
    'model-selection': [
        {id: 'home', label: 'Home', url: '/?replay=model-selection&from=home'},
        {id: 'models', label: 'Models', url: '/models?replay=model-selection&from=models'},
        {id: 'performance', label: 'Performance', url: '/datasets/plot-performance?replay=model-selection&from=performance&search_term=classification&type_query=true'},
        {id: 'datasets', label: 'Datasets', url: '/datasets/usages?replay=model-selection&from=datasets&search_term=PreprocessedDataset1'},
        {id: 'pipelines', label: 'Pipelines', url: '/pipelines?replay=model-selection&from=pipelines'},
        {id: 'editor', label: 'Editor', url: '/pipelines/edit-pipeline?replay=model-selection&from=editor&pipeline-name=PreprocessingPipeline1'},
        {id: 'chat', label: 'Chat', url: '/chat-with-mllo?replay=model-selection&from=chat'},
    ],
};

const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));
const REPLAY_STOPPED_MESSAGE = 'Replay stopped';

const getCenter = (element: Element): CursorPosition => {
    const rect = element.getBoundingClientRect();
    return {
        x: rect.left + rect.width / 2,
        y: rect.top + rect.height / 2,
    };
};

const setFieldValue = (element: HTMLInputElement | HTMLTextAreaElement, value: string) => {
    if (element instanceof HTMLTextAreaElement) {
        nativeTextAreaValueSetter?.call(element, value);
    } else {
        nativeInputValueSetter?.call(element, value);
    }
    element.dispatchEvent(new Event('input', {bubbles: true}));
    element.dispatchEvent(new Event('change', {bubbles: true}));
};

const getReplayId = () => new URLSearchParams(window.location.search).get('replay') ?? '';
const isReplayEnabled = () => getReplayId() in replaySectionsByDemo;

const DemoReplay: React.FC = () => {
    const [enabled, setEnabled] = useState(() => isReplayEnabled());
    const [cursor, setCursor] = useState<CursorPosition>({x: 88, y: 88});
    const [clicking, setClicking] = useState(false);
    const [paused, setPaused] = useState(false);
    const [collapsed, setCollapsed] = useState(false);
    const [status, setStatus] = useState<ReplayStatus>({
        step: 'Ready',
        detail: 'Open with ?replay=mnist to run the MNIST walkthrough.',
    });
    const cancelledRef = useRef(false);
    const pausedRef = useRef(false);
    const runIdRef = useRef(0);

    const prefersReducedMotion = useMemo(
        () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
        [],
    );
    const replayId = getReplayId();
    const replayTitle = replayId === 'model-selection' ? 'Model Selection Replay' : 'MNIST Replay';
    const replaySections = replaySectionsByDemo[replayId] ?? replaySectionsByDemo.mnist;

    useEffect(() => {
        const syncFromUrl = () => setEnabled(isReplayEnabled());
        window.addEventListener('popstate', syncFromUrl);
        return () => window.removeEventListener('popstate', syncFromUrl);
    }, []);

    const requestPause = () => {
        pausedRef.current = !paused;
        setPaused(!paused);
    };

    const requestStop = () => {
        runIdRef.current += 1;
        cancelledRef.current = true;
        pausedRef.current = false;
        setPaused(false);
        setEnabled(false);
        const params = new URLSearchParams(window.location.search);
        params.delete('replay');
        params.delete('from');
        const nextSearch = params.toString();
        window.history.replaceState(null, '', `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ''}`);
        window.dispatchEvent(new PopStateEvent('popstate'));
    };

    const seekTo = (section: ReplaySection) => {
        cancelledRef.current = true;
        pausedRef.current = false;
        setPaused(false);
        setStatus({step: `Seeking to ${section.label}`, detail: 'Restarting replay from the selected section.'});
        window.history.pushState(null, '', section.url);
        window.dispatchEvent(new PopStateEvent('popstate'));
        window.setTimeout(() => {
            cancelledRef.current = false;
            setEnabled(false);
            window.setTimeout(() => setEnabled(true), 0);
        }, 80);
    };

    useEffect(() => {
        if (!enabled) {
            return undefined;
        }

        const runId = runIdRef.current + 1;
        runIdRef.current = runId;
        cancelledRef.current = false;
        pausedRef.current = false;
        setPaused(false);

        const ensureActive = () => {
            if (cancelledRef.current || runIdRef.current !== runId) {
                throw new Error(REPLAY_STOPPED_MESSAGE);
            }
        };

        const query = <T extends Element>(selector: string): T | null => document.querySelector(selector) as T | null;
        const all = <T extends Element>(selector: string): T[] => Array.from(document.querySelectorAll(selector)) as T[];
        const isVisible = (element: Element | null): element is HTMLElement => {
            if (!(element instanceof HTMLElement)) {
                return false;
            }
            const rect = element.getBoundingClientRect();
            return rect.width > 0
                && rect.height > 0
                && rect.bottom > 0
                && rect.right > 0
                && rect.top < window.innerHeight
                && rect.left < window.innerWidth
                && window.getComputedStyle(element).visibility !== 'hidden';
        };
        const visibleAll = <T extends HTMLElement>(selector: string): T[] =>
            all<T>(selector).filter((element) => isVisible(element));

        const waitFor = async <T extends Element>(target: WaitTarget, timeout = 12000): Promise<T | null> => {
            const started = Date.now();
            while (!cancelledRef.current && Date.now() - started < timeout) {
                ensureActive();
                await waitIfPaused();
                if (typeof target === 'string') {
                    const element = query<T>(target);
                    if (element) {
                        return element;
                    }
                } else if (target()) {
                    return null;
                }
                await sleep(120);
            }
            return null;
        };

        const waitIfPaused = async () => {
            while (!cancelledRef.current && pausedRef.current) {
                ensureActive();
                setStatus((current) => ({
                    step: current.step.endsWith(' (Paused)') ? current.step : `${current.step} (Paused)`,
                    detail: 'Use Resume to continue, or seek to another section.',
                }));
                await sleep(160);
            }
        };

        const replaySleep = async (ms: number) => {
            const started = Date.now();
            while (!cancelledRef.current && Date.now() - started < ms) {
                ensureActive();
                await waitIfPaused();
                await sleep(Math.min(120, ms - (Date.now() - started)));
            }
            ensureActive();
        };

        const moveTo = async (target: Element | CursorPosition, delay = 650) => {
            ensureActive();
            const next = target instanceof Element ? getCenter(target) : target;
            await waitIfPaused();
            setCursor(next);
            await replaySleep(prefersReducedMotion ? 80 : delay);
        };

        const clickElement = async (element: HTMLElement, label: string) => {
            ensureActive();
            setStatus({step: label, detail: 'Moving cursor and clicking the real MLLE control.'});
            await moveTo(element);
            setClicking(true);
            element.click();
            await replaySleep(180);
            setClicking(false);
            await replaySleep(950);
        };

        const clickLink = async (element: HTMLAnchorElement, label: string, fallbackUrl: string) => {
            ensureActive();
            setStatus({step: label, detail: 'Moving cursor to the real MLLE navigation link.'});
            await moveTo(element);
            setClicking(true);
            await replaySleep(180);
            setClicking(false);
            window.history.pushState(null, '', fallbackUrl);
            window.dispatchEvent(new PopStateEvent('popstate'));
            await replaySleep(1200);
        };

        const typeInto = async (element: HTMLInputElement | HTMLTextAreaElement, value: string, label: string) => {
            ensureActive();
            setStatus({step: label, detail: `Typing "${value}" into the visible field.`});
            await moveTo(element);
            element.focus();
            setFieldValue(element, '');
            for (let i = 0; i < value.length; i += 1) {
                await waitIfPaused();
                if (cancelledRef.current) {
                    return;
                }
                setFieldValue(element, value.slice(0, i + 1));
                await replaySleep(prefersReducedMotion ? 8 : 42);
            }
            await replaySleep(500);
        };

        const clickSearchButtonNear = async (input: HTMLInputElement) => {
            const container = input.closest('.search-container');
            const button = container?.querySelector<HTMLButtonElement>('.search-button');
            if (button) {
                await clickElement(button, 'Run Search');
            }
        };

        const chooseSelectOption = async (select: HTMLSelectElement, value: string, label: string) => {
            setStatus({step: label, detail: `Selecting ${value} from a real MLLE control.`});
            await moveTo(select);
            select.value = value;
            select.dispatchEvent(new Event('change', {bubbles: true}));
            await replaySleep(900);
        };

        const clickButtonByText = async (text: string, label: string) => {
            const button = visibleAll<HTMLButtonElement>('button')
                .find((candidate) => candidate.textContent?.trim() === text);
            if (button) {
                await clickElement(button, label);
            }
            return button;
        };

        const navigateHome = async () => {
            if (window.location.pathname !== '/') {
                const currentReplay = getReplayId() || 'mnist';
                window.history.pushState(null, '', `/?replay=${currentReplay}&from=home`);
                window.dispatchEvent(new PopStateEvent('popstate'));
                await replaySleep(1200);
            }
        };

        const closeMenuIfOpen = async () => {
            const closeButton = query<HTMLButtonElement>('.close-button');
            if (isVisible(closeButton)) {
                await clickElement(closeButton, 'Prepare Canvas');
                await waitFor(() => !document.querySelector('.menu-container.open, .menu-container.mobile-open'), 4000);
            }
        };

        const scrollViewport = async (amount: number, label: string) => {
            setStatus({step: label, detail: 'Scrolling the real page to reveal linked evidence.'});
            setCursor({x: Math.min(window.innerWidth - 80, 420), y: Math.min(window.innerHeight - 140, 620)});
            await replaySleep(350);
            document.querySelector('.dashboard-content')?.scrollBy({top: amount, behavior: 'smooth'});
            await replaySleep(1500);
        };

        const hoverChartBars = async () => {
            const canvas = await waitFor<HTMLCanvasElement>('.chart-shell canvas', 12000);
            if (!canvas) {
                return;
            }

            const rect = canvas.getBoundingClientRect();
            const yHigh = rect.top + rect.height * 0.24;
            const yMid = rect.top + rect.height * 0.42;
            const yLow = rect.top + rect.height * 0.66;
            const points = [
                {
                    x: rect.left + rect.width * 0.18,
                    y: yHigh,
                    step: 'Hover CNN High Accuracy',
                    detail: 'Pause on a high-performing CNN result while you explain why MLModel1 is a strong starting candidate.',
                },
                {
                    x: rect.left + rect.width * 0.46,
                    y: yMid,
                    step: 'Hover Middle Results',
                    detail: 'Move across the comparison to discuss how performance changes by model and dataset condition.',
                },
                {
                    x: rect.left + rect.width * 0.74,
                    y: yLow,
                    step: 'Hover Weaker Results',
                    detail: 'Pause on lower bars to explain model sensitivity under noisier MNIST conditions.',
                },
                {
                    x: rect.left + rect.width * 0.28,
                    y: yHigh,
                    step: 'Select Evidence Point',
                    detail: 'Click one plotted evidence point so the selection panel updates with linked model, dataset, source, and score.',
                    click: true,
                },
            ];

            for (const point of points) {
                ensureActive();
                setStatus({step: point.step, detail: point.detail});
                await moveTo({x: point.x, y: point.y}, 900);
                canvas.dispatchEvent(new MouseEvent('mousemove', {
                    bubbles: true,
                    cancelable: true,
                    clientX: point.x,
                    clientY: point.y,
                    view: window,
                }));
                await replaySleep(point.click ? 450 : 2300);
                if (point.click) {
                    setClicking(true);
                    canvas.dispatchEvent(new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        clientX: point.x,
                        clientY: point.y,
                        view: window,
                    }));
                    await replaySleep(180);
                    setClicking(false);
                }
                await replaySleep(point.click ? 1400 : 400);
            }
        };

        const runModelSelection = async () => {
            const from = new URLSearchParams(window.location.search).get('from') || 'home';

            if (from === 'home') {
                await navigateHome();
                await replaySleep(900);
                await closeMenuIfOpen();
                setStatus({
                    step: 'Scenario',
                    detail: 'Imagine you are a data scientist choosing a starting model for handwritten digits.',
                });
                await moveTo({x: Math.min(window.innerWidth * 0.35, 360), y: 290});
                await replaySleep(1800);

                await waitFor(() => visibleAll<HTMLAnchorElement>('a[href="/models"]').length > 0, 10000);
                const modelTarget = visibleAll<HTMLAnchorElement>('a[href="/models"]')
                    .find((link) => link.textContent?.includes('Open Model Search'))
                    ?? visibleAll<HTMLAnchorElement>('a[href="/models"]')
                        .find((link) => link.textContent?.includes('Find Models'))
                    ?? null;
                if (modelTarget) {
                    await clickLink(modelTarget, 'Open Find Models', '/models?replay=model-selection&from=models');
                } else {
                    window.history.pushState(null, '', '/models?replay=model-selection&from=models');
                    window.dispatchEvent(new PopStateEvent('popstate'));
                    await replaySleep(1200);
                }
            }

            if (from === 'home' || from === 'models') {
                const modelInput = await waitFor<HTMLInputElement>('.search-input', 10000);
                if (!modelInput) return;
                await typeInto(modelInput, 'classification', 'Search Classification Models');
                await clickSearchButtonNear(modelInput);
                await waitFor(() => document.body.innerText.includes('matching models'), 14000);
                await scrollViewport(420, 'Show Candidate Models');
                setStatus({
                    step: 'Find Candidate Models',
                    detail: 'MLLE links the model records to MLLO concepts such as model objective, model type, and evaluation evidence.',
                });
                await replaySleep(3000);

                const menuButton = await waitFor<HTMLButtonElement>('.menu-icon', 8000);
                if (menuButton) {
                    await clickElement(menuButton, 'Open Navigation');
                }
                await waitFor(() => visibleAll<HTMLAnchorElement>('a[href="/datasets/plot-performance"]').length > 0, 8000);
                const performanceLink = visibleAll<HTMLAnchorElement>('a[href="/datasets/plot-performance"]')[0];
                if (performanceLink) {
                    await clickLink(performanceLink, 'Open Plot Performance', '/datasets/plot-performance?replay=model-selection&from=performance&search_term=classification&type_query=true');
                    await closeMenuIfOpen();
                }
            }

            if (from === 'home' || from === 'models' || from === 'performance') {
                await waitFor(() => document.body.innerText.includes('Controls'), 15000);
                const groupSelect = visibleAll<HTMLSelectElement>('select')
                    .find((select) => Array.from(select.options).some((option) => option.value === 'modelName'));
                if (groupSelect) {
                    await chooseSelectOption(groupSelect, 'modelName', 'Group by Model Name');
                }
                setStatus({
                    step: 'Compare Performance Evidence',
                    detail: 'Grouping by model name makes the MNIST decision visible: compare accuracy evidence across linked evaluations.',
                });
                await hoverChartBars();
                await scrollViewport(360, 'Show Performance Details');

                const menuButton = await waitFor<HTMLButtonElement>('.menu-icon', 8000);
                if (menuButton) {
                    await clickElement(menuButton, 'Open Navigation');
                }
                await waitFor(() => visibleAll<HTMLAnchorElement>('a[href="/datasets/usages"]').length > 0, 8000);
                const usagesLink = visibleAll<HTMLAnchorElement>('a[href="/datasets/usages"]')[0];
                if (usagesLink) {
                    await clickLink(usagesLink, 'Open Dataset Usages', '/datasets/usages?replay=model-selection&from=datasets&search_term=PreprocessedDataset1');
                    await closeMenuIfOpen();
                }
            }

            if (from === 'home' || from === 'models' || from === 'performance' || from === 'datasets') {
                await waitFor(() => document.body.innerText.includes('matching results'), 15000);
                setStatus({
                    step: 'Inspect Dataset Conditions',
                    detail: 'The linked MNIST datasets expose noise conditions such as G16, no noise, G48, G96, and Poisson noise.',
                });
                await scrollViewport(570, 'Show Noise and Usage Evidence');
                await replaySleep(3200);

                const menuButton = await waitFor<HTMLButtonElement>('.menu-icon', 8000);
                if (menuButton) {
                    await clickElement(menuButton, 'Open Navigation');
                }
                await waitFor(() => visibleAll<HTMLAnchorElement>('a[href="/pipelines"]').length > 0, 8000);
                const pipelineLink = visibleAll<HTMLAnchorElement>('a[href="/pipelines"]')
                    .find((link) => link.textContent?.includes('Find Pipelines'))
                    ?? visibleAll<HTMLAnchorElement>('a[href="/pipelines"]')[0];
                if (pipelineLink) {
                    await clickLink(pipelineLink, 'Open Pipelines', '/pipelines?replay=model-selection&from=pipelines');
                    await closeMenuIfOpen();
                }
            }

            if (from === 'home' || from === 'models' || from === 'performance' || from === 'datasets' || from === 'pipelines') {
                const pipelineInput = await waitFor<HTMLInputElement>('.search-input', 10000);
                if (!pipelineInput) return;
                await typeInto(pipelineInput, 'MLModel1', 'Search Model 1 Pipelines');
                await clickSearchButtonNear(pipelineInput);
                await waitFor(() => document.body.innerText.includes('Showing results for ML Model 1'), 14000);
                await scrollViewport(470, 'Show Pipeline Components');
                setStatus({
                    step: 'Trace Pipeline Evidence',
                    detail: 'The pipeline records connect the chosen model to training, execution, inputs, outputs, and lifecycle structure.',
                });
                await replaySleep(4200);

                const menuButton = await waitFor<HTMLButtonElement>('.menu-icon', 8000);
                if (menuButton) {
                    await clickElement(menuButton, 'Open Navigation');
                }
                await waitFor(() => visibleAll<HTMLAnchorElement>('a[href="/pipelines/edit-pipeline"]').length > 0, 8000);
                const editorLink = visibleAll<HTMLAnchorElement>('a[href="/pipelines/edit-pipeline"]')[0];
                if (editorLink) {
                    await clickLink(editorLink, 'Open Pipeline Editor', '/pipelines/edit-pipeline?replay=model-selection&from=editor&pipeline-name=PreprocessingPipeline1');
                    await closeMenuIfOpen();
                }
            }

            if (from === 'home' || from === 'models' || from === 'performance' || from === 'datasets' || from === 'pipelines' || from === 'editor') {
                await waitFor(() => document.body.innerText.includes('Pipeline Canvas'), 16000);
                setStatus({
                    step: 'Extra: Preprocessing Pipeline Editor',
                    detail: 'The editor shows the richer MNIST data-preprocessing workflow: input data, reshaping, scaling, casting, output data, and downstream model.',
                });
                await scrollViewport(360, 'Show Editable Pipeline Canvas');
                const firstNode = visibleAll<HTMLElement>('.pipeline-node')[0];
                if (firstNode) {
                    await clickElement(firstNode, 'Inspect Pipeline Node');
                }
                await clickButtonByText('Reasoning', 'Show Ontology Checks');
                await replaySleep(2500);

                const menuButton = await waitFor<HTMLButtonElement>('.menu-icon', 8000);
                if (menuButton) {
                    await clickElement(menuButton, 'Open Navigation');
                }
                await waitFor(() => visibleAll<HTMLAnchorElement>('a[href="/chat-with-mllo"]').length > 0, 8000);
                const chatLink = visibleAll<HTMLAnchorElement>('a[href="/chat-with-mllo"]')
                    .find((link) => link.textContent?.includes('Chat with MLLO'))
                    ?? visibleAll<HTMLAnchorElement>('a[href="/chat-with-mllo"]')[0];
                if (chatLink) {
                    await clickLink(chatLink, 'Open Chat with MLLO', '/chat-with-mllo?replay=model-selection&from=chat');
                    await closeMenuIfOpen();
                }
            }

            if (from === 'home' || from === 'models' || from === 'performance' || from === 'datasets' || from === 'pipelines' || from === 'editor' || from === 'chat') {
                setStatus({
                    step: 'Extra: Chat with MLLO',
                    detail: 'Scroll to the composer so the prompt can be staged without depending on a live LLM response.',
                });
                const content = document.querySelector('.dashboard-content');
                content?.scrollTo({top: content.scrollHeight, behavior: 'smooth'});
                await replaySleep(1300);
                const chatInput = await waitFor<HTMLTextAreaElement>('textarea', 10000);
                if (!chatInput) return;
                await typeInto(
                    chatInput,
                    'Compare pipelines PreprocessingPipeline1 and PreprocessingPipeline10.',
                    'Ask Chat with MLLO',
                );
                const sendButton = visibleAll<HTMLButtonElement>('button')
                    .find((button) => button.textContent?.trim() === 'Send');
                if (sendButton) {
                    setStatus({
                        step: 'Extra: Chat with MLLO',
                        detail: 'The prompt is staged in Chat with MLLO; leave it unsent during recording if the LLM service is not available.',
                    });
                    await moveTo(sendButton, 800);
                    await replaySleep(2200);
                }
                setStatus({
                    step: 'Extra: Chat with MLLO',
                    detail: 'Chat with MLLO shows how the same ontology-grounded graph can be queried conversationally.',
                });
                await scrollViewport(320, 'Show Chat Prompt');
                await replaySleep(3800);
            }

            setStatus({
                step: 'Replay Complete',
                detail: 'The demo selected MLModel1 from connected MNIST evidence, then showed preprocessing editing and Chat with MLLO.',
            });
        };

        const run = async () => {
            try {
                if (getReplayId() === 'model-selection') {
                    await runModelSelection();
                    return;
                }

                const from = new URLSearchParams(window.location.search).get('from') || 'home';
                if (from === 'home') {
                    await navigateHome();
                    await replaySleep(900);
                    await closeMenuIfOpen();

                    setStatus({step: 'Home', detail: 'Start from the MLLE workbench overview.'});
                    await moveTo({x: Math.min(window.innerWidth * 0.35, 360), y: 290});
                    await replaySleep(1100);

                    await waitFor(() => visibleAll<HTMLAnchorElement>('a[href="/models"]').length > 0, 10000);
                    const modelTarget = visibleAll<HTMLAnchorElement>('a[href="/models"]')
                        .find((link) => link.textContent?.includes('Open Model Search'))
                        ?? visibleAll<HTMLAnchorElement>('a[href="/models"]')
                            .find((link) => link.textContent?.includes('Find Models'))
                        ?? null;
                    if (modelTarget) {
                        await clickLink(modelTarget, 'Open Model Search', '/models?replay=mnist&from=models');
                    } else {
                        window.history.pushState(null, '', '/models?replay=mnist&from=models');
                        window.dispatchEvent(new PopStateEvent('popstate'));
                        await replaySleep(1200);
                    }
                }

                if (from === 'home' || from === 'models') {
                    const modelInput = await waitFor<HTMLInputElement>('.search-input', 10000);
                    if (!modelInput) return;
                    await typeInto(modelInput, 'MLModel1', 'Search Model');
                    await clickSearchButtonNear(modelInput);
                    await waitFor(() => document.body.innerText.includes('Focused on ML Model 1'), 14000);
                    await scrollViewport(520, 'Show Model Evidence');
                    await scrollViewport(420, 'Show Linked Datasets');

                    const datasetChip = visibleAll<HTMLButtonElement>('.model-explorer-chip')
                        .find((button) => button.textContent?.trim() === 'Preprocessed Dataset 1');
                    if (datasetChip) {
                        await clickElement(datasetChip, 'Open Dataset Evidence');
                    }
                }

                if (from === 'home' || from === 'models' || from === 'datasets') {
                    if (from === 'datasets') {
                        await waitFor<HTMLInputElement>('.search-input', 10000);
                    }
                    await waitFor(() => window.location.pathname === '/datasets/usages', 12000);
                    await waitFor(() => document.body.innerText.includes('matching results'), 14000);
                    await scrollViewport(570, 'Show Dataset Usage Results');

                    const menuButton = await waitFor<HTMLButtonElement>('.menu-icon', 8000);
                    if (menuButton) {
                        await clickElement(menuButton, 'Open Navigation');
                    }
                    await waitFor(() => visibleAll<HTMLAnchorElement>('a[href="/pipelines"]').length > 0, 8000);
                    const pipelineLink = visibleAll<HTMLAnchorElement>('a[href="/pipelines"]')
                        .find((link) => link.textContent?.includes('Find Pipelines'))
                        ?? visibleAll<HTMLAnchorElement>('a[href="/pipelines"]')[0];
                    if (pipelineLink) {
                        await clickLink(pipelineLink, 'Open Pipelines', '/pipelines?replay=mnist&from=pipelines');
                        await closeMenuIfOpen();
                    }
                }

                if (from === 'home' || from === 'models' || from === 'datasets' || from === 'pipelines') {
                    const pipelineInput = await waitFor<HTMLInputElement>('.search-input', 10000);
                    if (!pipelineInput) return;
                    await typeInto(pipelineInput, 'MLModel1', 'Search Pipelines');
                    await clickSearchButtonNear(pipelineInput);
                    await waitFor(() => document.body.innerText.includes('Showing results for ML Model 1'), 14000);
                    await scrollViewport(470, 'Show Pipeline Evidence');

                    const nextMenuButton = await waitFor<HTMLButtonElement>('.menu-icon', 8000);
                    if (nextMenuButton) {
                        await clickElement(nextMenuButton, 'Open Navigation');
                    }
                    await waitFor(() => visibleAll<HTMLAnchorElement>('a[href="/chat-with-mllo"]').length > 0, 8000);
                    const chatLink = visibleAll<HTMLAnchorElement>('a[href="/chat-with-mllo"]')
                        .find((link) => link.textContent?.includes('Chat with MLLO'))
                        ?? visibleAll<HTMLAnchorElement>('a[href="/chat-with-mllo"]')[0];
                    if (chatLink) {
                        await clickLink(chatLink, 'Open Chat with MLLO', '/chat-with-mllo?replay=mnist&from=chat');
                        await closeMenuIfOpen();
                    }
                }

                const chatInput = await waitFor<HTMLTextAreaElement>('textarea', 10000);
                if (!chatInput) return;
                await typeInto(
                    chatInput,
                    'Show me models with performance more than 0.9, their test dataset, and their pipeline.',
                    'Ask Audit Question',
                );
                const sendButton = all<HTMLButtonElement>('button')
                    .find((button) => button.textContent?.trim() === 'Send');
                if (sendButton) {
                    await clickElement(sendButton, 'Send Question');
                }
                await waitFor(() => !document.body.innerText.includes('Thinking…'), 45000);
                await scrollViewport(420, 'Show Returned Evidence');

                setStatus({
                    step: 'Replay Complete',
                    detail: 'The walkthrough used real MLLE pages, searches, clicks, scrolling, and GraphDB-backed results.',
                });
            } catch (error) {
                if (error instanceof Error && error.message === REPLAY_STOPPED_MESSAGE) {
                    return;
                }
                setStatus({
                    step: 'Replay Stopped',
                    detail: error instanceof Error ? error.message : 'The replay stopped unexpectedly.',
                });
            }
        };

        void run();

        return () => {
            cancelledRef.current = true;
        };
    }, [enabled, prefersReducedMotion]);

    if (!enabled) {
        return null;
    }

    return (
        <>
            <div
                className={`demo-replay-cursor${clicking ? ' is-clicking' : ''}`}
                style={{transform: `translate(${cursor.x}px, ${cursor.y}px)`}}
                aria-hidden="true"
            />
            <aside className="demo-replay-status" aria-live="polite">
                <div className="demo-replay-header">
                    <div>
                        <span>{replayTitle}</span>
                        <strong>{status.step}</strong>
                    </div>
                    <button
                        type="button"
                        className="demo-replay-collapse"
                        onClick={() => setCollapsed((value) => !value)}
                        aria-expanded={!collapsed}
                    >
                        {collapsed ? 'Expand' : 'Collapse'}
                    </button>
                </div>
                {!collapsed && (
                    <>
                        <p>{status.detail}</p>
                        <div className="demo-replay-controls">
                    <button type="button" onClick={requestPause}>
                        {paused ? 'Resume' : 'Pause'}
                    </button>
                    <button type="button" onClick={requestStop}>
                        Stop
                    </button>
                </div>
                <div className="demo-replay-seek" aria-label="Seek replay">
                    {replaySections.map((section) => (
                        <button key={section.id} type="button" onClick={() => seekTo(section)}>
                            {section.label}
                        </button>
                    ))}
                </div>
                    </>
                )}
            </aside>
        </>
    );
};

export default DemoReplay;
