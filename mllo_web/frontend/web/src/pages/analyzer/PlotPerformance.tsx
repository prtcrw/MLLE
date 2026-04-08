import React, {useEffect, useMemo, useState} from 'react';
import {Bar, Line} from 'react-chartjs-2';
import {
    BarElement,
    CategoryScale,
    Chart as ChartJS,
    Filler,
    Legend,
    LinearScale,
    LineElement,
    PointElement,
    Title,
    Tooltip
} from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import {buildV1Url} from '../../services/api';
import LoadingBar from '../../components/LoadingBar.tsx';
import './styles/plot_performance.css';

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    LineElement,
    Filler,
    PointElement,
    Title,
    Tooltip,
    Legend,
    ChartDataLabels
);

type PerformancePoint = {
    datasetName: string;
    modelPerformanceValue: number;
    modelName: string;
    modelType: string;
    rawData: string;
    categoryLabel: string;
};

type PerformanceMetrics = Record<string, PerformancePoint[]>;

type PlotMode = 'auto' | 'bar' | 'line';
type SortOrder = 'Ascending' | 'Descending';
type GroupBy = 'default' | 'rawData' | 'datasetName' | 'modelName' | 'modelType';

const GROUP_LABELS: Record<GroupBy, string> = {
    default: 'Performance',
    rawData: 'Raw Data',
    datasetName: 'Dataset Name',
    modelName: 'Model Name',
    modelType: 'Model Type',
};

const makeCategoryLabel = (datasetName: string, rawData: string) => {
    const safeDataset = datasetName?.trim() || 'Unknown Dataset';
    const safeRaw = rawData?.trim();
    if (!safeRaw || safeRaw === safeDataset) {
        return safeDataset;
    }
    return `${safeDataset} - ${safeRaw}`;
};

const convertToCamelCase = (data: Record<string, any[]>): PerformanceMetrics => {
    const camelCaseData: PerformanceMetrics = {};

    for (const metric in data) {
        if (!Object.prototype.hasOwnProperty.call(data, metric)) {
            continue;
        }

        camelCaseData[metric] = data[metric].map((item: any) => {
            const datasetName = item['dataset_name'] ?? '';
            const rawData = item['raw_data'] ?? '';

            return {
                datasetName,
                modelName: item['model_name'] ?? 'Unknown Model',
                modelType: item['model_type'] ?? 'Unknown Type',
                rawData,
                modelPerformanceValue: Number.parseFloat(item['model_performance_value'] ?? '0'),
                categoryLabel: makeCategoryLabel(datasetName, rawData),
            };
        });
    }

    return camelCaseData;
};

const generateColorPalette = (numColors: number): string[] => {
    if (numColors <= 0) {
        return [];
    }

    const colors: string[] = [];
    for (let i = 0; i < numColors; i += 1) {
        const hue = (i * 360 / numColors + 18) % 360;
        colors.push(`hsl(${hue}, 72%, 48%)`);
    }
    return colors;
};

const formatMetricName = (metric: string) =>
    metric
        .replace(/[_-]+/g, ' ')
        .replace(/\b\w/g, (char) => char.toUpperCase());

const formatScore = (value: number | null | undefined) =>
    typeof value === 'number' && Number.isFinite(value) ? value.toFixed(3) : 'n/a';

const getTickDensityConfig = (labelCount: number, plotMode: 'bar' | 'line') => {
    if (labelCount <= 8) {
        return {
            autoSkip: false,
            maxTicksLimit: labelCount,
            maxRotation: 0,
        };
    }

    if (labelCount <= 16) {
        return {
            autoSkip: false,
            maxTicksLimit: labelCount,
            maxRotation: plotMode === 'bar' ? 0 : 30,
        };
    }

    if (labelCount <= 28) {
        return {
            autoSkip: true,
            maxTicksLimit: 14,
            maxRotation: 45,
        };
    }

    return {
        autoSkip: true,
        maxTicksLimit: 10,
        maxRotation: 55,
    };
};

const wrapAxisLabel = (label: string, maxLineLength = 18) => {
    const words = label.split(/\s+/).filter(Boolean);
    if (words.length <= 1 && label.length <= maxLineLength) {
        return label;
    }

    const lines: string[] = [];
    let currentLine = '';

    for (const word of words) {
        const nextLine = currentLine ? `${currentLine} ${word}` : word;
        if (nextLine.length > maxLineLength && currentLine) {
            lines.push(currentLine);
            currentLine = word;
        } else {
            currentLine = nextLine;
        }
    }

    if (currentLine) {
        lines.push(currentLine);
    }

    return lines;
};

const PlotPerformance: React.FC = () => {
    const [plotMode, setPlotMode] = useState<PlotMode>('auto');
    const [metric, setMetric] = useState('');
    const [performanceCutoff, setPerformanceCutoff] = useState(0);
    const [orderBy, setOrderBy] = useState<SortOrder>('Descending');
    const [groupBy, setGroupBy] = useState<GroupBy>('default');
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedModel, setSelectedModel] = useState('all');
    const [selectedRawData, setSelectedRawData] = useState('all');
    const [selectedPoint, setSelectedPoint] = useState<PerformancePoint | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [fetchedData, setFetchedData] = useState<PerformanceMetrics | null>(null);
    const [metricOptions, setMetricOptions] = useState<string[]>([]);
    const [colorMapping, setColorMapping] = useState<Record<string, string>>({});
    const [minCutoff, setMinCutoff] = useState(0);
    const [maxCutoff, setMaxCutoff] = useState(1);

    useEffect(() => {
        const fetchData = async () => {
            setIsLoading(true);
            try {
                const queryParams = new URLSearchParams(window.location.search);
                const response = await fetch(buildV1Url(`datasets/performances/?${queryParams.toString()}`));
                const payload = await response.json();
                const performanceByMetric = convertToCamelCase(payload['model_performance_metric'] ?? {});
                const nextMetricOptions = Object.keys(performanceByMetric);
                const initialMetric = nextMetricOptions[0] ?? '';
                const allModels = Array.from(
                    new Set(
                        nextMetricOptions.flatMap((metricKey) =>
                            (performanceByMetric[metricKey] ?? []).map((point) => point.modelName)
                        )
                    )
                );
                const palette = generateColorPalette(allModels.length);
                const nextColorMapping = allModels.reduce<Record<string, string>>((mapping, modelName, index) => {
                    mapping[modelName] = palette[index % palette.length];
                    return mapping;
                }, {});

                setFetchedData(performanceByMetric);
                setMetricOptions(nextMetricOptions);
                setMetric(initialMetric);
                setColorMapping(nextColorMapping);
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, []);

    const metricData = useMemo(() => {
        if (!fetchedData || !metric) {
            return [];
        }
        return fetchedData[metric] ?? [];
    }, [fetchedData, metric]);

    useEffect(() => {
        if (metricData.length === 0) {
            return;
        }

        const values = metricData
            .map((item) => item.modelPerformanceValue)
            .filter((value) => Number.isFinite(value));
        const nextMin = Math.min(...values);
        const nextMax = Math.max(...values);

        setMinCutoff(nextMin);
        setMaxCutoff(nextMax);
        setPerformanceCutoff((current) => {
            if (current < nextMin || current > nextMax) {
                return nextMin;
            }
            return current;
        });
    }, [metricData]);

    useEffect(() => {
        if (!selectedPoint) {
            return;
        }

        const exists = metricData.some((item) =>
            item.modelName === selectedPoint.modelName &&
            item.categoryLabel === selectedPoint.categoryLabel &&
            item.modelPerformanceValue === selectedPoint.modelPerformanceValue
        );

        if (!exists) {
            setSelectedPoint(null);
        }
    }, [metricData, selectedPoint]);

    const modelOptions = useMemo(
        () => ['all', ...Array.from(new Set(metricData.map((item) => item.modelName))).sort((a, b) => a.localeCompare(b))],
        [metricData]
    );

    const rawDataOptions = useMemo(
        () => ['all', ...Array.from(new Set(metricData.map((item) => item.rawData || 'Unknown'))).sort((a, b) => a.localeCompare(b))],
        [metricData]
    );

    const filteredEntries = useMemo(() => {
        return metricData.filter((item) => {
            const normalizedRawData = item.rawData || 'Unknown';
            const haystack = `${item.datasetName} ${item.modelName} ${item.modelType} ${normalizedRawData}`.toLowerCase();
            return item.modelPerformanceValue >= performanceCutoff
                && (selectedModel === 'all' || item.modelName === selectedModel)
                && (selectedRawData === 'all' || normalizedRawData === selectedRawData)
                && (!searchTerm.trim() || haystack.includes(searchTerm.trim().toLowerCase()));
        });
    }, [metricData, performanceCutoff, selectedModel, selectedRawData, searchTerm]);

    const rankedEntries = useMemo(() => {
        const grouped = filteredEntries.reduce<Record<string, PerformancePoint[]>>((acc, item) => {
            const groupKey = groupBy === 'default' ? 'all' : item[groupBy];
            if (!acc[groupKey]) {
                acc[groupKey] = [];
            }
            acc[groupKey].push(item);
            return acc;
        }, {});

        const sortedGroupKeys = Object.keys(grouped).sort((a, b) => {
            if (groupBy === 'default') {
                return 0;
            }
            return a.localeCompare(b);
        });

        return sortedGroupKeys.flatMap((groupKey) => {
            const points = [...grouped[groupKey]];
            points.sort((a, b) => {
                if (orderBy === 'Ascending') {
                    return a.modelPerformanceValue - b.modelPerformanceValue;
                }
                return b.modelPerformanceValue - a.modelPerformanceValue;
            });
            return points;
        });
    }, [filteredEntries, groupBy, orderBy]);

    const summary = useMemo(() => {
        if (rankedEntries.length === 0) {
            return {
                visiblePoints: 0,
                visibleModels: 0,
                visibleSources: 0,
                averageScore: null as number | null,
                bestPoint: null as PerformancePoint | null,
            };
        }

        const total = rankedEntries.reduce((sum, item) => sum + item.modelPerformanceValue, 0);
        return {
            visiblePoints: rankedEntries.length,
            visibleModels: new Set(rankedEntries.map((item) => item.modelName)).size,
            visibleSources: new Set(rankedEntries.map((item) => item.rawData || 'Unknown')).size,
            averageScore: total / rankedEntries.length,
            bestPoint: [...rankedEntries].sort((a, b) => b.modelPerformanceValue - a.modelPerformanceValue)[0] ?? null,
        };
    }, [rankedEntries]);

    const activePlotMode = useMemo<'bar' | 'line'>(() => {
        if (plotMode !== 'auto') {
            return plotMode;
        }
        return rankedEntries.length > 12 ? 'line' : 'bar';
    }, [plotMode, rankedEntries.length]);

    const chartState = useMemo(() => {
        const labels = Array.from(new Set(rankedEntries.map((item) => item.categoryLabel)));
        const modelNames = Array.from(new Set(rankedEntries.map((item) => item.modelName)));
        const pointMap = new Map<string, PerformancePoint>();

        const datasets = modelNames.map((modelName) => {
            const values = labels.map((label) => {
                const point = rankedEntries.find((item) => item.modelName === modelName && item.categoryLabel === label) ?? null;
                if (point) {
                    pointMap.set(`${modelName}::${label}`, point);
                }
                return point ? point.modelPerformanceValue : null;
            });

            return {
                label: modelName,
                data: values,
                borderColor: colorMapping[modelName] ?? '#1f5eff',
                backgroundColor: colorMapping[modelName] ?? '#1f5eff',
                borderWidth: 2,
                pointRadius: activePlotMode === 'line' ? 4 : 0,
                pointHoverRadius: 6,
                pointBackgroundColor: colorMapping[modelName] ?? '#1f5eff',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                tension: 0.28,
                fill: false,
                spanGaps: true,
                maxBarThickness: 34,
                borderRadius: activePlotMode === 'bar' ? 10 : 0,
            };
        });

        return {labels, datasets, pointMap};
    }, [rankedEntries, colorMapping, activePlotMode]);

    const chartOptions = useMemo(() => {
        const tickDensity = getTickDensityConfig(chartState.labels.length, activePlotMode);

        return {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'nearest' as const,
                intersect: true,
            },
            onClick: (_event: unknown, elements: any[], chart: any) => {
                if (!elements.length) {
                    return;
                }

                const element = elements[0];
                const datasetLabel = chart.data.datasets[element.datasetIndex]?.label;
                const categoryLabel = chart.data.labels[element.index];
                const point = chartState.pointMap.get(`${datasetLabel}::${categoryLabel}`) ?? null;
                setSelectedPoint(point);
            },
            plugins: {
                legend: {
                    position: 'bottom' as const,
                    labels: {
                        usePointStyle: true,
                        boxWidth: 10,
                        padding: 18,
                    }
                },
                tooltip: {
                    callbacks: {
                        title: (items: any[]) => {
                            const item = items[0];
                            const datasetLabel = item?.dataset?.label;
                            const categoryLabel = item?.label;
                            const point = chartState.pointMap.get(`${datasetLabel}::${categoryLabel}`) ?? null;
                            return point?.datasetName ?? categoryLabel;
                        },
                        label: (context: any) => {
                            const datasetLabel = context.dataset?.label;
                            const categoryLabel = context.label;
                            const point = chartState.pointMap.get(`${datasetLabel}::${categoryLabel}`) ?? null;
                            if (!point) {
                                return `${datasetLabel}: ${context.raw}`;
                            }
                            return [
                                `${point.modelName}: ${formatScore(point.modelPerformanceValue)}`,
                                `Type: ${point.modelType}`,
                                `Source: ${point.rawData || 'Unknown'}`,
                            ];
                        }
                    },
                    filter: (context: any) => context.raw !== null && context.raw !== undefined,
                },
                datalabels: {
                    display: chartState.labels.length <= 10,
                    anchor: 'end' as const,
                    align: 'top' as const,
                    formatter: (value: number | null) => (value === null ? '' : value.toFixed(2)),
                    color: '#19304f',
                    font: {
                        weight: 'bold' as const,
                        size: 11,
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#274567',
                        autoSkip: tickDensity.autoSkip,
                        maxTicksLimit: tickDensity.maxTicksLimit,
                        callback: (_value: string | number, index: number) => {
                            const label = chartState.labels[index] ?? '';
                            return tickDensity.autoSkip ? label : wrapAxisLabel(label);
                        },
                        maxRotation: tickDensity.maxRotation,
                        minRotation: 0,
                    },
                    grid: {
                        display: false,
                    }
                },
                y: {
                    suggestedMin: minCutoff,
                    suggestedMax: maxCutoff,
                    ticks: {
                        color: '#274567',
                    },
                    grid: {
                        color: 'rgba(43, 84, 123, 0.12)',
                    },
                    title: {
                        display: true,
                        text: formatMetricName(metric),
                    }
                }
            }
        };
    }, [chartState, activePlotMode, minCutoff, maxCutoff, metric]);

    const detailPoint = selectedPoint ?? summary.bestPoint;

    return (
        <>
            <LoadingBar isLoading={isLoading}/>
            <div className="plot-performance-page">
                <div className="plot-performance-layout">
                    <aside className="filters-panel">
                        <div className="panel-header">
                            <h2>Controls</h2>
                            <p>{metric ? formatMetricName(metric) : 'Loading metrics...'}</p>
                        </div>

                        <div className="filter-grid">
                            <label className="filter-field">
                                <span>Visualization</span>
                                <select value={plotMode} onChange={(e) => setPlotMode(e.target.value as PlotMode)}>
                                    <option value="auto">Auto</option>
                                    <option value="bar">Bar</option>
                                    <option value="line">Line</option>
                                </select>
                            </label>

                            <label className="filter-field">
                                <span>Metric</span>
                                <select value={metric} onChange={(e) => setMetric(e.target.value)}>
                                    {metricOptions.map((item) => (
                                        <option key={item} value={item}>{formatMetricName(item)}</option>
                                    ))}
                                </select>
                            </label>

                            <label className="filter-field">
                                <span>Order</span>
                                <select value={orderBy} onChange={(e) => setOrderBy(e.target.value as SortOrder)}>
                                    <option value="Descending">Top First</option>
                                    <option value="Ascending">Low First</option>
                                </select>
                            </label>

                            <label className="filter-field">
                                <span>Group</span>
                                <select value={groupBy} onChange={(e) => setGroupBy(e.target.value as GroupBy)}>
                                    <option value="default">{GROUP_LABELS.default}</option>
                                    <option value="rawData">{GROUP_LABELS.rawData}</option>
                                    <option value="datasetName">{GROUP_LABELS.datasetName}</option>
                                    <option value="modelName">{GROUP_LABELS.modelName}</option>
                                    <option value="modelType">{GROUP_LABELS.modelType}</option>
                                </select>
                            </label>

                            <label className="filter-field filter-field-full">
                                <span>Search</span>
                                <input
                                    type="text"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    placeholder="Dataset, model, type, source"
                                />
                            </label>

                            <label className="filter-field">
                                <span>Model</span>
                                <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
                                    {modelOptions.map((item) => (
                                        <option key={item} value={item}>{item === 'all' ? 'All Models' : item}</option>
                                    ))}
                                </select>
                            </label>

                            <label className="filter-field">
                                <span>Raw Data</span>
                                <select value={selectedRawData} onChange={(e) => setSelectedRawData(e.target.value)}>
                                    {rawDataOptions.map((item) => (
                                        <option key={item} value={item}>{item === 'all' ? 'All Sources' : item}</option>
                                    ))}
                                </select>
                            </label>
                        </div>

                        <div className="cutoff-panel">
                            <div className="cutoff-header">
                                <span>Performance Cutoff</span>
                                <strong>{performanceCutoff.toFixed(3)}</strong>
                            </div>
                            <input
                                type="range"
                                min={minCutoff}
                                max={maxCutoff}
                                value={performanceCutoff}
                                step={0.001}
                                onChange={(e) => setPerformanceCutoff(Number(e.target.value))}
                            />
                            <div className="cutoff-scale">
                                <span>{minCutoff.toFixed(3)}</span>
                                <span>{maxCutoff.toFixed(3)}</span>
                            </div>
                        </div>

                        <div className="detail-panel">
                            <div className="panel-header">
                                <h2>Selection</h2>
                                <p>{selectedPoint ? 'Clicked point' : 'Current best visible result'}</p>
                            </div>
                            {detailPoint ? (
                                <div className="detail-card">
                                    <strong>{detailPoint.modelName}</strong>
                                    <span>{detailPoint.modelType}</span>
                                    <dl>
                                        <div>
                                            <dt>Dataset</dt>
                                            <dd>{detailPoint.datasetName}</dd>
                                        </div>
                                        <div>
                                            <dt>Source</dt>
                                            <dd>{detailPoint.rawData || 'Unknown'}</dd>
                                        </div>
                                        <div>
                                            <dt>Metric</dt>
                                            <dd>{formatMetricName(metric)}</dd>
                                        </div>
                                        <div>
                                            <dt>Score</dt>
                                            <dd>{formatScore(detailPoint.modelPerformanceValue)}</dd>
                                        </div>
                                    </dl>
                                </div>
                            ) : (
                                <p className="empty-state">No visible data after the current filters.</p>
                            )}
                        </div>
                    </aside>

                    <section className="visualization-panel">
                        <div className="panel-header">
                            <h2>Interactive Plot</h2>
                            <p>{plotMode === 'auto' ? `Auto selected ${activePlotMode} view` : `${activePlotMode} view`}</p>
                        </div>

                        {chartState.labels.length > 0 ? (
                            <div className="chart-shell">
                                {activePlotMode === 'bar' ? (
                                    <Bar data={{labels: chartState.labels, datasets: chartState.datasets}} options={chartOptions}/>
                                ) : (
                                    <Line data={{labels: chartState.labels, datasets: chartState.datasets}} options={chartOptions}/>
                                )}
                            </div>
                        ) : (
                            <div className="empty-state empty-state-large">No results match the current filters.</div>
                        )}

                        <div className="results-panel">
                            <div className="panel-header">
                                <h2>Ranked Results</h2>
                                <p>Top visible runs update as you filter the plot.</p>
                            </div>

                            <div className="results-table">
                                <div className="results-table-head">
                                    <span>Rank</span>
                                    <span>Model</span>
                                    <span>Dataset</span>
                                    <span>Source</span>
                                    <span>Score</span>
                                </div>
                                {rankedEntries.slice(0, 12).map((item, index) => (
                                    <button
                                        key={`${item.modelName}-${item.categoryLabel}-${index}`}
                                        type="button"
                                        className={`results-row${selectedPoint === item ? ' is-active' : ''}`}
                                        onClick={() => setSelectedPoint(item)}
                                    >
                                        <span>{index + 1}</span>
                                        <span>{item.modelName}</span>
                                        <span>{item.datasetName}</span>
                                        <span>{item.rawData || 'Unknown'}</span>
                                        <strong>{formatScore(item.modelPerformanceValue)}</strong>
                                    </button>
                                ))}
                                {rankedEntries.length === 0 && (
                                    <div className="empty-state">No ranked rows available.</div>
                                )}
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        </>
    );
};

export default PlotPerformance;
