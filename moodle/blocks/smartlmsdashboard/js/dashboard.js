(function() {
    var INTERVENTION_THRESHOLD = 0.50;
    var NEAR_THRESHOLD_MARGIN = 0.05;
    var HIGH_RISK_THRESHOLD = 0.66;
    var RISK_DRIVER_DOMINANCE_MARGIN = 0.08;
    var DEFAULT_RISK_BUBBLE_FILTER = 'all';
    var DEFAULT_RISK_BUBBLE_TOP_N = 15;
    var DEFAULT_RISK_BUBBLE_THRESHOLD = 0.50;
    var RISK_BUBBLE_ZOOM_DRAG_THRESHOLD = 18;
    var RISK_BUBBLE_MIN_ZOOM_RANGE = 0.06;
    var DEFAULT_COURSE_CONFIG = {
        teachingMode: 'Medium',
        earlyEngagementNotifications: {
            week1: true,
            week2: true,
            week3: true
        },
        riskThreshold: DEFAULT_RISK_BUBBLE_THRESHOLD,
        notificationTypes: {
            newHighRisk: true,
            noLmsActivity: true
        },
        notificationFrequency: 'Weekly summary',
        isConfigured: false
    };
    var RISK_DISTRIBUTION_COLORS = {
        normal: [
            'rgba(13, 110, 253, 0.42)',
            'rgba(220, 53, 69, 0.48)'
        ],
        selected: [
            'rgba(13, 110, 253, 0.82)',
            'rgba(220, 53, 69, 0.82)'
        ],
        dimmed: [
            'rgba(13, 110, 253, 0.16)',
            'rgba(220, 53, 69, 0.18)'
        ],
        border: [
            'rgba(13, 110, 253, 0.72)',
            'rgba(220, 53, 69, 0.72)'
        ],
        selectedBorder: [
            'rgba(13, 110, 253, 1)',
            'rgba(220, 53, 69, 1)'
        ]
    };

    var riskZoneThresholds = [
        {
            key: 'high',
            min: 0.66,
            max: 1.0,
            chartColor: 'rgba(220, 53, 69, 0.10)',
            badgeClass: 'is-high',
            finalLabel: 'High Final Risk',
            zoneLabel: 'High Zone'
        },
        {
            key: 'medium',
            min: 0.33,
            max: 0.66,
            chartColor: 'rgba(255, 193, 7, 0.10)',
            badgeClass: 'is-medium',
            finalLabel: 'Medium Final Risk',
            zoneLabel: 'Medium Zone'
        },
        {
            key: 'low',
            min: 0.0,
            max: 0.33,
            chartColor: 'rgba(25, 135, 84, 0.10)',
            badgeClass: 'is-low',
            finalLabel: 'Low Final Risk',
            zoneLabel: 'Low Zone'
        }
    ];

    var queryRegion = function(root, region) {
        return root.querySelector('[data-region="' + region + '"]');
    };

    var queryRegions = function(root, selector) {
        return Array.prototype.slice.call(root.querySelectorAll(selector));
    };

    var setText = function(element, value) {
        if (element) {
            element.textContent = value;
        }
    };

    var clamp = function(value, min, max) {
        return Math.max(min, Math.min(max, value));
    };

    var stableNoise = function(seedText, salt) {
        var hash = 0;
        var raw = seedText + '|' + salt;
        var i;

        for (i = 0; i < raw.length; i++) {
            hash = ((hash << 5) - hash) + raw.charCodeAt(i);
            hash |= 0;
        }

        return ((Math.abs(hash % 1000) / 1000) * 2) - 1;
    };

    var escapeHtml = function(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    };

    var getZoneConfig = function(score) {
        var i;

        for (i = 0; i < riskZoneThresholds.length; i++) {
            if (score >= riskZoneThresholds[i].min && score <= riskZoneThresholds[i].max) {
                return riskZoneThresholds[i];
            }
        }

        return riskZoneThresholds[riskZoneThresholds.length - 1];
    };

    var formatPercentTick = function(value) {
        return (value * 100).toFixed(0) + '%';
    };

    var formatRate = function(count, total) {
        return total ? ((count / total) * 100).toFixed(1) + '%' : '0.0%';
    };

    var buildRiskDistributionFromPoints = function(points) {
        var safeCount = points.filter(function(point) {
            return Number(point.label) !== 1;
        }).length;
        var atRiskCount = points.filter(function(point) {
            return Number(point.label) === 1;
        }).length;

        return {
            labels: [0, 1],
            values: [safeCount, atRiskCount]
        };
    };

    var getCourseLabel = function(courseKey, points) {
        var match = (points || []).find(function(point) {
            return String(point.coursekey || '') === String(courseKey || '') && point.courselabel;
        });

        if (match) {
            return match.courselabel;
        }

        return courseKey ? 'Unit ' + courseKey : 'Unit not recorded';
    };

    var getCourseConfig = function(courseConfigs, courseKey, courseLabel) {
        var savedConfig = (courseConfigs || {})[courseKey] || {};
        var engagement = savedConfig.earlyEngagementNotifications || {};
        var notificationTypes = savedConfig.notificationTypes || {};

        return {
            courseKey: courseKey || '',
            courseLabel: savedConfig.courseLabel || courseLabel || '',
            teachingMode: savedConfig.teachingMode || DEFAULT_COURSE_CONFIG.teachingMode,
            earlyEngagementNotifications: {
                week1: engagement.week1 !== undefined ? !!engagement.week1 : DEFAULT_COURSE_CONFIG.earlyEngagementNotifications.week1,
                week2: engagement.week2 !== undefined ? !!engagement.week2 : DEFAULT_COURSE_CONFIG.earlyEngagementNotifications.week2,
                week3: engagement.week3 !== undefined ? !!engagement.week3 : DEFAULT_COURSE_CONFIG.earlyEngagementNotifications.week3
            },
            riskThreshold: savedConfig.riskThreshold !== undefined && savedConfig.riskThreshold !== null ?
                Number(savedConfig.riskThreshold) : DEFAULT_COURSE_CONFIG.riskThreshold,
            notificationTypes: {
                newHighRisk: notificationTypes.newHighRisk !== undefined ? !!notificationTypes.newHighRisk : DEFAULT_COURSE_CONFIG.notificationTypes.newHighRisk,
                noLmsActivity: notificationTypes.noLmsActivity !== undefined ? !!notificationTypes.noLmsActivity : DEFAULT_COURSE_CONFIG.notificationTypes.noLmsActivity
            },
            notificationFrequency: savedConfig.notificationFrequency || DEFAULT_COURSE_CONFIG.notificationFrequency,
            isConfigured: !!savedConfig.isConfigured
        };
    };

    var pluralize = function(count, singular, plural) {
        return count + ' ' + (count === 1 ? singular : plural);
    };

    var setList = function(element, items) {
        if (element) {
            element.innerHTML = items.map(function(item) {
                return '<li>' + escapeHtml(item) + '</li>';
            }).join('');
        }
    };

    var formatSnapshotDate = function(rawDate) {
        var parsed;

        if (!rawDate) {
            return 'Not recorded';
        }

        parsed = new Date(String(rawDate).replace(' ', 'T'));
        if (Number.isNaN(parsed.getTime())) {
            return String(rawDate);
        }

        return parsed.toLocaleDateString(undefined, {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    };

    var formatStoredConfidence = function(confidence) {
        var numeric;

        if (confidence === null || confidence === undefined || confidence === '') {
            return null;
        }

        numeric = Number(confidence);
        if (Number.isNaN(numeric)) {
            return String(confidence).charAt(0).toUpperCase() + String(confidence).slice(1);
        }

        if (numeric > 1) {
            numeric = numeric / 100;
        }

        if (numeric >= 0.75) {
            return 'High';
        }
        if (numeric >= 0.55) {
            return 'Moderate';
        }
        return 'Low';
    };

    var calculatePredictionConfidence = function(points) {
        var averageCertainty;

        if (!points.length) {
            return 'Not available';
        }

        averageCertainty = points.reduce(function(sum, point) {
            return sum + (Math.abs(Number(point.risk) - 0.5) * 2);
        }, 0) / points.length;

        if (averageCertainty >= 0.66) {
            return 'High';
        }
        if (averageCertainty >= 0.33) {
            return 'Moderate';
        }
        return 'Low';
    };

    var buildAtRiskTable = function(root, bubblePoints, bubbleApi) {
        var body = queryRegion(root, 'at-risk-table-body');
        var count = queryRegion(root, 'at-risk-count');
        var searchEl = queryRegion(root, 'at-risk-search');
        var sortEl = queryRegion(root, 'at-risk-sort');
        var pageSizeEl = queryRegion(root, 'at-risk-pagesize');
        var exportEl = queryRegion(root, 'at-risk-export');
        var prevEl = queryRegion(root, 'at-risk-prev');
        var nextEl = queryRegion(root, 'at-risk-next');
        var statusEl = queryRegion(root, 'at-risk-pagination-status');
        var headerButtons = queryRegions(root, '.risk-bubble-table th button[data-sort-key]');
        var atRiskStudents;
        var state;
        var render;
        var applySort;
        var getFilteredData;
        var exportCsv;

        if (!body || !count || !searchEl || !sortEl || !pageSizeEl || !exportEl || !prevEl || !nextEl || !statusEl) {
            return;
        }

        atRiskStudents = [];

        state = {
            query: '',
            sortKey: 'risk',
            sortDirection: 'desc',
            page: 1,
            pageSize: Number(pageSizeEl.value),
            selectedStudentId: null
        };

        var setPoints = function(points) {
            bubblePoints = points || [];
            atRiskStudents = bubblePoints.filter(function(point) {
                return Number(point.label) === 1;
            });
        };

        applySort = function(list) {
            return list.slice().sort(function(a, b) {
                var left = a[state.sortKey];
                var right = b[state.sortKey];
                var compare;

                if (typeof left === 'string' || typeof right === 'string') {
                    left = String(left || '').toLowerCase();
                    right = String(right || '').toLowerCase();
                    compare = left.localeCompare(right, undefined, {numeric: true, sensitivity: 'base'});
                } else {
                    compare = Number(left) - Number(right);
                }

                return state.sortDirection === 'asc' ? compare : compare * -1;
            });
        };

        getFilteredData = function() {
            var filtered = atRiskStudents;
            var query = state.query.toLowerCase();

            if (query) {
                filtered = filtered.filter(function(student) {
                    return String(student.studentid).toLowerCase().indexOf(query) !== -1 ||
                        String(student.student || '').toLowerCase().indexOf(query) !== -1 ||
                        String(student.email || '').toLowerCase().indexOf(query) !== -1;
                });
            }

            return applySort(filtered);
        };

        exportCsv = function(rows) {
            var header = ['Student ID', 'Name', 'Email', 'Final Risk', 'Behaviour Risk', 'Academic Risk'];
            var lines = [header].concat(rows.map(function(student) {
                return [
                    student.studentid,
                    student.student,
                    student.email || 'N/A',
                    student.risk.toFixed(2),
                    student.x.toFixed(2),
                    student.y.toFixed(2)
                ];
            }));
            var csv = lines.map(function(line) {
                return line.map(function(value) {
                    return '"' + String(value).replace(/"/g, '""') + '"';
                }).join(',');
            }).join('\n');
            var blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
            var url = window.URL.createObjectURL(blob);
            var link = document.createElement('a');

            link.href = url;
            link.download = 'at-risk-students.csv';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        };

        render = function() {
            var filtered = getFilteredData();
            var total = filtered.length;
            var totalPages = Math.max(1, Math.ceil(total / state.pageSize));
            var startIndex;
            var endIndex;
            var paged;
            var rows;

            if (state.page > totalPages) {
                state.page = totalPages;
            }

            startIndex = (state.page - 1) * state.pageSize;
            endIndex = startIndex + state.pageSize;
            paged = filtered.slice(startIndex, endIndex);

            setText(count, total + ' students');

            if (!paged.length) {
                body.innerHTML = '<tr><td colspan="6">' +
                    (atRiskStudents.length ? 'No students matched the current search.' :
                        'No at-risk students found for the current unit selection.') +
                    '</td></tr>';
            } else {
                rows = paged.map(function(student) {
                    var isSelected = state.selectedStudentId !== null && String(state.selectedStudentId) === String(student.studentid);
                    return '<tr data-student-id="' + escapeHtml(student.studentid) + '" class="' + (isSelected ? 'is-selected' : '') + '">' +
                        '<td>' + escapeHtml(student.studentid) + '</td>' +
                        '<td>' + escapeHtml(student.student) + '</td>' +
                        '<td>' + escapeHtml(student.email || 'N/A') + '</td>' +
                        '<td>' + escapeHtml(student.risk.toFixed(2)) + '</td>' +
                        '<td>' + escapeHtml(student.x.toFixed(2)) + '</td>' +
                        '<td>' + escapeHtml(student.y.toFixed(2)) + '</td>' +
                        '</tr>';
                });
                body.innerHTML = rows.join('');
            }

            setText(statusEl, total ?
                'Showing ' + (startIndex + 1) + '-' + Math.min(endIndex, total) + ' of ' + total + ' students' :
                'Showing 0 of 0 students');
            prevEl.disabled = state.page <= 1;
            nextEl.disabled = state.page >= totalPages;

            queryRegions(body, 'tr[data-student-id]').forEach(function(row) {
                row.addEventListener('click', function() {
                    var studentId = row.getAttribute('data-student-id');
                    state.selectedStudentId = studentId;
                    render();
                    if (bubbleApi && typeof bubbleApi.focusStudentById === 'function') {
                        bubbleApi.focusStudentById(studentId);
                    }
                });
            });
        };

        setPoints(bubblePoints);

        searchEl.addEventListener('input', function() {
            state.query = searchEl.value.trim();
            state.page = 1;
            render();
        });

        sortEl.addEventListener('change', function() {
            var parts = sortEl.value.split('-');
            state.sortKey = parts[0];
            state.sortDirection = parts[1] || 'asc';
            state.page = 1;
            render();
        });

        pageSizeEl.addEventListener('change', function() {
            state.pageSize = Number(pageSizeEl.value);
            state.page = 1;
            render();
        });

        exportEl.addEventListener('click', function() {
            exportCsv(getFilteredData());
        });

        prevEl.addEventListener('click', function() {
            if (state.page > 1) {
                state.page -= 1;
                render();
            }
        });

        nextEl.addEventListener('click', function() {
            var totalPages = Math.max(1, Math.ceil(getFilteredData().length / state.pageSize));
            if (state.page < totalPages) {
                state.page += 1;
                render();
            }
        });

        headerButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                var sortKey = button.getAttribute('data-sort-key');
                if (state.sortKey === sortKey) {
                    state.sortDirection = state.sortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    state.sortKey = sortKey;
                    state.sortDirection = sortKey === 'student' || sortKey === 'email' || sortKey === 'studentid' ? 'asc' : 'desc';
                }
                sortEl.value = state.sortKey + '-' + state.sortDirection;
                state.page = 1;
                render();
            });
        });

        render();

        return {
            setSelectedStudentId: function(studentId) {
                state.selectedStudentId = studentId;
                render();
            },
            clearSelectedStudentId: function() {
                state.selectedStudentId = null;
                render();
            },
            updatePoints: function(points) {
                setPoints(points);
                state.selectedStudentId = null;
                state.page = 1;
                render();
            }
        };
    };

    var buildAiInsightSummary = function(root, riskDistribution, bubblePoints, predictionMetadata, hasSelectedUnit, courseConfig) {
        var summaryEl = queryRegion(root, 'ai-insight-summary');
        var snapshotDateEl = queryRegion(root, 'ai-insight-snapshot-date');
        var modelVersionEl = queryRegion(root, 'ai-insight-model-version');
        var confidenceEl = queryRegion(root, 'ai-insight-confidence');
        var distributionEl = queryRegion(root, 'ai-insight-distribution');
        var mapEl = queryRegion(root, 'ai-insight-map');
        var tableEl = queryRegion(root, 'ai-insight-table');
        var userSummaryEl = queryRegion(root, 'ai-insight-user-summary');
        var chartInterpretationEl = queryRegion(root, 'ai-insight-chart-interpretation');
        var actionTemplateEl = queryRegion(root, 'ai-insight-action-template');
        var labels = riskDistribution.labels || [];
        var values = riskDistribution.values || [];
        var total = 0;
        var safeCount = 0;
        var atRiskCount = 0;
        var highFinalRiskCount;
        var highBehaviourRiskCount;
        var highAcademicRiskCount;
        var atRiskStudents;
        var nearThresholdCount;
        var behaviourEarlyWarningCount;
        var averageAcademicRisk;
        var averageBehaviourRisk;
        var atRiskRate;
        var atRiskPercent;
        var primaryConcern;
        var riskStatusText;
        var driverText;
        var interventionText;
        var confidenceLabel;
        var interventionThreshold = courseConfig && !Number.isNaN(Number(courseConfig.riskThreshold)) ?
            Number(courseConfig.riskThreshold) : DEFAULT_RISK_BUBBLE_THRESHOLD;
        var isLowLmsDependency = courseConfig && courseConfig.teachingMode === 'Low';
        var lmsContextText = ' Prediction results are decision-support indicators, not direct evidence of disengagement. For this unit, Moodle activity should be reviewed with other teaching evidence.';
        var lowLmsDriverText = 'LMS engagement is treated as a weak signal for this unit.';
        var findings;
        var actions;

        predictionMetadata = predictionMetadata || {};

        if (!snapshotDateEl || !modelVersionEl || !confidenceEl ||
                !distributionEl || !mapEl || !tableEl || !userSummaryEl ||
                !chartInterpretationEl || !actionTemplateEl) {
            return;
        }

        setText(snapshotDateEl, formatSnapshotDate(predictionMetadata.snapshotDate));
        setText(modelVersionEl, predictionMetadata.modelVersion || 'Not recorded');

        if (!hasSelectedUnit) {
            if (summaryEl) {
                summaryEl.hidden = true;
            }
            setText(confidenceEl, formatStoredConfidence(predictionMetadata.predictionConfidence) || 'Not available');
            return;
        }

        if (summaryEl) {
            summaryEl.hidden = false;
        }

        values.forEach(function(value, index) {
            var numericValue = Number(value) || 0;
            total += numericValue;

            if (Number(labels[index]) === 1) {
                atRiskCount += numericValue;
            } else {
                safeCount += numericValue;
            }
        });

        if (!total && bubblePoints.length) {
            total = bubblePoints.length;
            atRiskCount = bubblePoints.filter(function(point) {
                return Number(point.label) === 1;
            }).length;
            safeCount = total - atRiskCount;
        }

        atRiskRate = formatRate(atRiskCount, total);
        atRiskPercent = total ? (atRiskCount / total) * 100 : 0;
        atRiskStudents = bubblePoints.filter(function(point) {
            return Number(point.label) === 1;
        });
        highFinalRiskCount = bubblePoints.filter(function(point) {
            return Number(point.risk) >= HIGH_RISK_THRESHOLD;
        }).length;
        highBehaviourRiskCount = atRiskStudents.filter(function(point) {
            return Number(point.x) >= HIGH_RISK_THRESHOLD;
        }).length;
        highAcademicRiskCount = atRiskStudents.filter(function(point) {
            return Number(point.y) >= HIGH_RISK_THRESHOLD;
        }).length;
        nearThresholdCount = bubblePoints.filter(function(point) {
            return Number(point.risk) >= interventionThreshold - NEAR_THRESHOLD_MARGIN &&
                Number(point.risk) < interventionThreshold;
        }).length;
        behaviourEarlyWarningCount = atRiskStudents.filter(function(point) {
            return Number(point.x) >= HIGH_RISK_THRESHOLD && Number(point.y) < HIGH_RISK_THRESHOLD;
        }).length;
        averageAcademicRisk = atRiskStudents.length ? atRiskStudents.reduce(function(sum, point) {
            return sum + Number(point.y);
        }, 0) / atRiskStudents.length : 0;
        averageBehaviourRisk = atRiskStudents.length ? atRiskStudents.reduce(function(sum, point) {
            return sum + Number(point.x);
        }, 0) / atRiskStudents.length : 0;

        if (atRiskCount === 0) {
            riskStatusText = 'Overall cohort risk is low in the latest prediction snapshot.';
        } else if (atRiskPercent < 20) {
            riskStatusText = 'Overall cohort risk remains low, with a small group requiring targeted review.';
        } else if (atRiskPercent >= 40) {
            riskStatusText = 'Student risk is elevated across the cohort. Early intervention is recommended.';
        } else {
            riskStatusText = 'A meaningful intervention group has been identified and should be reviewed before the next prediction cycle.';
        }

        if (!atRiskStudents.length) {
            primaryConcern = 'None detected';
            driverText = 'No dominant risk driver is visible because no students are currently flagged as at risk.';
            interventionText = 'routine monitoring can continue until the next prediction cycle.';
        } else if (averageAcademicRisk >= averageBehaviourRisk + RISK_DRIVER_DOMINANCE_MARGIN ||
                highAcademicRiskCount > highBehaviourRiskCount) {
            primaryConcern = 'Academic risk';
            driverText = 'Academic risk is the dominant contributor for most flagged students.';
            interventionText = 'early intervention should focus primarily on academic support.';
        } else if (averageBehaviourRisk >= averageAcademicRisk + RISK_DRIVER_DOMINANCE_MARGIN ||
                highBehaviourRiskCount > highAcademicRiskCount) {
            primaryConcern = 'Behaviour risk';
            driverText = 'Behaviour risk is leading academic risk, suggesting declining engagement before significant academic deterioration.';
            interventionText = 'early intervention should focus primarily on engagement and attendance support.';
        } else {
            primaryConcern = 'Mixed risk';
            driverText = 'Academic and behavioural risk are both contributing, so intervention should consider performance and engagement together.';
            interventionText = 'early intervention should combine academic support with engagement follow-up.';
        }

        confidenceLabel = formatStoredConfidence(predictionMetadata.predictionConfidence) ||
            calculatePredictionConfidence(bubblePoints);

        setText(confidenceEl, confidenceLabel);
        setText(distributionEl, pluralize(total, 'student', 'students'));
        setText(mapEl, atRiskRate);
        setText(tableEl, primaryConcern);
        setText(userSummaryEl, 'Of ' + total + ' analysed students, ' + atRiskCount + ' (' + atRiskRate +
            ') are currently classified as at risk. ' + (isLowLmsDependency ? lowLmsDriverText : driverText) +
            ' This indicates that ' + interventionText +
            (isLowLmsDependency ? lmsContextText : ''));

        findings = [
            isLowLmsDependency ?
                'LMS engagement is treated as a weak signal for this unit, so Moodle activity patterns should be interpreted alongside other teaching evidence.' :
                driverText,
            isLowLmsDependency ?
                'Behaviour risk may be less reliable for this unit because important engagement may happen outside Moodle.' :
                (behaviourEarlyWarningCount ?
                'Several students show high behavioural risk with comparatively lower academic risk, which may indicate declining engagement before performance drops.' :
                'The current flagged group does not show a large behavioural early-warning subgroup.'),
            highFinalRiskCount ?
                'The intervention list includes students with high final risk scores requiring immediate review.' :
                'Most flagged students are below the high final-risk band, but still require monitoring.'
        ];

        if (nearThresholdCount) {
            findings.push(pluralize(nearThresholdCount, 'student is', 'students are') +
                ' within ' + NEAR_THRESHOLD_MARGIN.toFixed(2) + ' of the ' +
                interventionThreshold.toFixed(2) + ' intervention threshold and should be watched in the next prediction cycle.');
        }

        actions = [
            'Review students with the highest final risk scores first.',
            highAcademicRiskCount && highBehaviourRiskCount ?
                'Contact students with both high behavioural and academic risk.' :
                'Use the primary concern to choose the first support action for each flagged student.',
            nearThresholdCount ?
                'Monitor students near the intervention threshold during the next prediction cycle.' :
                'Recheck the cohort after the next prediction refresh.'
        ];

        setList(chartInterpretationEl, findings);
        setList(actionTemplateEl, actions);
    };

    var initRiskDistribution = function(root, riskDistribution) {
        var canvas = queryRegion(root, 'risk-chart');
        var summaryCards = queryRegions(root, '[data-risk-index]');
        var labels = [];
        var values = [];
        var total = 0;
        var chart;
        var centerPlugin;
        var selectedRiskIndex = null;
        var setSelectedRiskIndex;
        var clearSelectedRiskIndex;
        var updateChartColors;
        var applyDistribution;
        var getOrCreateTooltip;
        var renderExternalTooltip;

        if (!canvas || typeof Chart === 'undefined') {
            return null;
        }

        applyDistribution = function(distribution) {
            var rawLabels = distribution.labels || [];
            var rawValues = distribution.values || [];
            var safeIndex;
            var atRiskIndex;
            var safeCount;
            var atRiskCount;
            var safeRate;
            var atRiskRate;

            labels = rawLabels.map(function(label) {
                return Number(label) === 1 ? 'At-Risk Students' : 'Not At-Risk Students';
            });
            values = rawValues.map(function(value) {
                return Number(value) || 0;
            });
            total = values.reduce(function(sum, value) {
                return sum + value;
            }, 0);
            safeIndex = labels.indexOf('Not At-Risk Students');
            atRiskIndex = labels.indexOf('At-Risk Students');
            safeCount = safeIndex >= 0 ? values[safeIndex] : 0;
            atRiskCount = atRiskIndex >= 0 ? values[atRiskIndex] : 0;
            safeRate = total ? ((safeCount / total) * 100).toFixed(1) : '0.0';
            atRiskRate = total ? ((atRiskCount / total) * 100).toFixed(1) : '0.0';

            setText(queryRegion(root, 'risk-summary-safe-count'), String(safeCount));
            setText(queryRegion(root, 'risk-summary-atrisk-count'), String(atRiskCount));
            setText(queryRegion(root, 'risk-summary-safe-rate'), safeRate + '%');
            setText(queryRegion(root, 'risk-summary-atrisk-rate'), atRiskRate + '%');
            setText(queryRegion(root, 'risk-summary-focus'), 'Total: ' + total);
        };

        applyDistribution(riskDistribution);

        var setActiveSummaryCards = function(activeIndex) {
            summaryCards.forEach(function(card) {
                card.classList.toggle('is-active', Number(card.getAttribute('data-risk-index')) === activeIndex);
            });
        };

        updateChartColors = function(currentChart) {
            var dataset = currentChart.data.datasets[0];
            dataset.backgroundColor = values.map(function(value, index) {
                if (selectedRiskIndex === null) {
                    return RISK_DISTRIBUTION_COLORS.normal[index];
                }
                return selectedRiskIndex === index ?
                    RISK_DISTRIBUTION_COLORS.selected[index] :
                    RISK_DISTRIBUTION_COLORS.dimmed[index];
            });
            dataset.borderColor = values.map(function(value, index) {
                return selectedRiskIndex === index ?
                    RISK_DISTRIBUTION_COLORS.selectedBorder[index] :
                    RISK_DISTRIBUTION_COLORS.border[index];
            });
        };

        clearSelectedRiskIndex = function(currentChart) {
            var tooltipEl = currentChart.canvas.parentNode.querySelector('.risk-distribution-tooltip');

            selectedRiskIndex = null;
            updateChartColors(currentChart);
            currentChart.setActiveElements([]);
            setActiveSummaryCards(null);
            setText(queryRegion(root, 'risk-summary-focus'), 'Total: ' + total);
            if (tooltipEl) {
                tooltipEl.style.opacity = 0;
            }
            currentChart.update();
        };

        setSelectedRiskIndex = function(index) {
            if (selectedRiskIndex === index) {
                clearSelectedRiskIndex(chart);
                return;
            }

            selectedRiskIndex = index;
            updateChartColors(chart);
            chart.setActiveElements([{datasetIndex: 0, index: selectedRiskIndex}]);
            chart.update();
        };

        getOrCreateTooltip = function(currentChart) {
            var parent = currentChart.canvas.parentNode;
            var tooltipEl = parent.querySelector('.risk-distribution-tooltip');

            if (tooltipEl) {
                return tooltipEl;
            }

            tooltipEl = document.createElement('div');
            tooltipEl.className = 'risk-distribution-tooltip';
            tooltipEl.innerHTML = '<span class="risk-distribution-tooltip-count"></span>' +
                '<span class="risk-distribution-tooltip-rate"></span>';
            parent.appendChild(tooltipEl);
            return tooltipEl;
        };

        renderExternalTooltip = function(context) {
            var currentChart = context.chart;
            var tooltip = context.tooltip;
            var tooltipEl = getOrCreateTooltip(currentChart);
            var dataPoint;
            var rawValue;
            var percentage;
            var parentRect;
            var canvasRect;
            var tooltipWidth;
            var tooltipHeight;
            var centerX;
            var placeRight;
            var x;
            var y;

            if (!tooltip || tooltip.opacity === 0 || !tooltip.dataPoints || !tooltip.dataPoints.length) {
                tooltipEl.style.opacity = 0;
                return;
            }

            dataPoint = tooltip.dataPoints[0];
            rawValue = Number(dataPoint.raw) || 0;
            percentage = total ? ((rawValue / total) * 100).toFixed(1) : '0.0';

            setText(tooltipEl.querySelector('.risk-distribution-tooltip-count'),
                pluralize(rawValue, 'student', 'students'));
            setText(tooltipEl.querySelector('.risk-distribution-tooltip-rate'),
                percentage + '% of cohort');

            parentRect = currentChart.canvas.parentNode.getBoundingClientRect();
            canvasRect = currentChart.canvas.getBoundingClientRect();
            tooltipWidth = tooltipEl.offsetWidth || 118;
            tooltipHeight = tooltipEl.offsetHeight || 48;
            centerX = currentChart.chartArea.left + ((currentChart.chartArea.right - currentChart.chartArea.left) / 2);
            placeRight = tooltip.caretX < centerX;
            x = (canvasRect.left - parentRect.left) + tooltip.caretX + (placeRight ? 18 : -18 - tooltipWidth);
            y = (canvasRect.top - parentRect.top) + tooltip.caretY - tooltipHeight - 14;

            if (y < 8) {
                y = (canvasRect.top - parentRect.top) + tooltip.caretY + 14;
            }

            x = clamp(x, 8, parentRect.width - tooltipWidth - 8);
            y = clamp(y, 8, parentRect.height - tooltipHeight - 8);

            tooltipEl.style.opacity = 1;
            tooltipEl.style.left = x + 'px';
            tooltipEl.style.top = y + 'px';
            tooltipEl.style.transform = 'none';
        };

        centerPlugin = {
            id: 'riskChartCenterLabelPlugin',
            afterDraw: function(currentChart) {
                var meta = currentChart.getDatasetMeta(0);
                var arc = meta && meta.data && meta.data[0];
                var ctx;
                var centerX;
                var centerY;
                var activeElement;
                var hasActiveSlice;
                var activeIndex;
                var activeValue;
                var activeLabel;
                var activePercent;

                if (!arc) {
                    return;
                }

                ctx = currentChart.ctx;
                centerX = arc.x;
                centerY = arc.y;
                activeElement = currentChart.getActiveElements()[0];
                hasActiveSlice = !!activeElement || selectedRiskIndex !== null;
                activeIndex = activeElement ? activeElement.index : selectedRiskIndex;
                activeValue = hasActiveSlice ? currentChart.data.datasets[0].data[activeIndex] : total;
                activeLabel = hasActiveSlice ? currentChart.data.labels[activeIndex] : 'Total Students';
                activePercent = hasActiveSlice && total ? ((activeValue / total) * 100).toFixed(1) + '%' : 'students';

                setActiveSummaryCards(hasActiveSlice ? activeIndex : null);
                setText(queryRegion(root, 'risk-summary-focus'), hasActiveSlice ?
                    activeLabel + ': ' + activeValue + ' (' + activePercent + ')' :
                    'Total: ' + total);

                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = '#64748b';
                ctx.font = '600 12px sans-serif';
                ctx.fillText(activeLabel, centerX, centerY - 12);
                ctx.fillStyle = '#0f172a';
                ctx.font = '700 24px sans-serif';
                ctx.fillText(String(activeValue), centerX, centerY + 4);
                ctx.fillStyle = hasActiveSlice ? '#475569' : '#64748b';
                ctx.font = '600 11px sans-serif';
                ctx.fillText(activePercent, centerX, centerY + 24);
                ctx.restore();
            }
        };

        chart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Student Distribution',
                    data: values,
                    backgroundColor: RISK_DISTRIBUTION_COLORS.normal,
                    hoverBackgroundColor: RISK_DISTRIBUTION_COLORS.selected,
                    borderColor: RISK_DISTRIBUTION_COLORS.border,
                    hoverBorderColor: RISK_DISTRIBUTION_COLORS.selectedBorder,
                    borderWidth: 2,
                    hoverOffset: 10,
                    spacing: 2
                }]
            },
            plugins: [centerPlugin],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '62%',
                onHover: function(event, activeElements, currentChart) {
                    if (event.native && event.native.target) {
                        event.native.target.style.cursor = activeElements.length ? 'pointer' : 'default';
                    }
                    currentChart.draw();
                },
                onClick: function(event, activeElements, currentChart) {
                    var clickedElements = currentChart.getElementsAtEventForMode(
                        event,
                        'nearest',
                        {intersect: true},
                        true
                    );

                    if (!clickedElements.length) {
                        clearSelectedRiskIndex(currentChart);
                        return;
                    }

                    setSelectedRiskIndex(clickedElements[0].index);
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        onClick: function(event, legendItem) {
                            setSelectedRiskIndex(legendItem.index);
                        },
                        labels: {
                            usePointStyle: true,
                            boxWidth: 10,
                            padding: 18,
                            color: '#334155',
                            font: {
                                size: 12,
                                weight: '600'
                            }
                        }
                    },
                    tooltip: {
                        enabled: false,
                        external: renderExternalTooltip
                    }
                }
            }
        });

        summaryCards.forEach(function(card) {
            card.addEventListener('click', function() {
                var index = Number(card.getAttribute('data-risk-index'));
                setSelectedRiskIndex(index);
            });
        });

        if (canvas.closest('.risk-distribution-card')) {
            canvas.closest('.risk-distribution-card').addEventListener('click', function(event) {
                if (event.target === canvas) {
                    return;
                }
                clearSelectedRiskIndex(chart);
            });
        }

        return {
            chart: chart,
            updateData: function(distribution) {
                selectedRiskIndex = null;
                applyDistribution(distribution || {labels: [], values: []});
                chart.data.labels = labels;
                chart.data.datasets[0].data = values;
                updateChartColors(chart);
                chart.setActiveElements([]);
                chart.update();
            }
        };
    };

    var initRiskBubble = function(root, bubblePoints, feedbackConfig) {
        var canvas = queryRegion(root, 'risk-bubble-chart');
        var filterEl = queryRegion(root, 'risk-bubble-filter');
        var topNControlEl = queryRegion(root, 'risk-bubble-topn-control');
        var topNEl = queryRegion(root, 'risk-bubble-topn');
        var topNValueEl = queryRegion(root, 'risk-bubble-topn-value');
        var thresholdEl = queryRegion(root, 'risk-bubble-threshold');
        var thresholdValueEl = queryRegion(root, 'risk-bubble-threshold-value');
        var jitterEl = queryRegion(root, 'risk-bubble-jitter');
        var clusterEl = queryRegion(root, 'risk-bubble-cluster');
        var resetZoomEl = queryRegion(root, 'risk-bubble-reset-zoom');
        var mapResetEl = queryRegion(root, 'risk-bubble-map-reset');
        var lowLmsNoteEl = queryRegion(root, 'risk-bubble-low-lms-note');
        var selectionNoteEl = queryRegion(root, 'risk-bubble-selection-note');
        var selectionBadgeEl = queryRegion(root, 'risk-bubble-selection-badge');
        var selectionZoneBadgeEl = queryRegion(root, 'risk-bubble-selection-zone-badge');
        var clearSelectionEl = queryRegion(root, 'risk-bubble-clear-selection');
        var selectionStudentEl = queryRegion(root, 'risk-bubble-selection-student');
        var selectionStudentIdEl = queryRegion(root, 'risk-bubble-selection-studentid');
        var selectionEmailEl = queryRegion(root, 'risk-bubble-selection-email');
        var selectionRiskEl = queryRegion(root, 'risk-bubble-selection-risk');
        var selectionBehaviourEl = queryRegion(root, 'risk-bubble-selection-behaviour');
        var selectionAcademicEl = queryRegion(root, 'risk-bubble-selection-academic');
        var clusterListEl = queryRegion(root, 'risk-bubble-cluster-list');
        var clusterListTitleEl = queryRegion(root, 'risk-bubble-cluster-title');
        var clusterListOptionsEl = queryRegion(root, 'risk-bubble-cluster-options');
        var feedbackPanelEl = queryRegion(root, 'uc-feedback-panel');
        var feedbackFormEl = queryRegion(root, 'uc-feedback-form');
        var feedbackStatusEl = queryRegion(root, 'uc-feedback-status');
        var feedbackSubmitEl = queryRegion(root, 'uc-feedback-submit');
        var feedbackPredictionIdEl = queryRegion(root, 'uc-feedback-prediction-id');
        var feedbackStudentKeyEl = queryRegion(root, 'uc-feedback-student-key');
        var feedbackCourseKeyEl = queryRegion(root, 'uc-feedback-course-key');
        var feedbackSnapshotDateEl = queryRegion(root, 'uc-feedback-snapshot-date');
        var chart;
        var currentSelectedStudentId = null;
        var currentSelectedPoint = null;
        var currentSelectedClusterPoint = null;
        var currentRiskThreshold = DEFAULT_RISK_BUBBLE_THRESHOLD;
        var defaultScaleRange = {
            min: -0.05,
            max: 1.05
        };
        var riskBubbleTooltipPosition = 'average';
        var registerTooltipPositioner = function() {
            if (!Chart.Tooltip || !Chart.Tooltip.positioners ||
                    Chart.Tooltip.positioners.riskBubbleSmartPosition) {
                if (Chart.Tooltip && Chart.Tooltip.positioners &&
                        Chart.Tooltip.positioners.riskBubbleSmartPosition) {
                    riskBubbleTooltipPosition = 'riskBubbleSmartPosition';
                }
                return;
            }

            Chart.Tooltip.positioners.riskBubbleSmartPosition = function(elements) {
                var element = elements && elements.length ? elements[0].element : null;
                var currentChart = this.chart || this._chart;
                var chartArea = currentChart && currentChart.chartArea;
                var pointX;
                var pointY;
                var radius;
                var horizontalInset = 130;
                var verticalInset = 36;
                var offset = 14;
                var canPlaceAbove;
                var preferLeftSide;
                var x;
                var y;
                var xAlign = 'center';
                var yAlign = 'bottom';

                if (!element || !chartArea) {
                    return false;
                }

                pointX = element.x;
                pointY = element.y;
                radius = Number(element.options && element.options.radius) || 8;
                canPlaceAbove = pointY - chartArea.top > 76;
                preferLeftSide = pointX > chartArea.left + ((chartArea.right - chartArea.left) * 0.5);

                if (canPlaceAbove) {
                    x = clamp(pointX, chartArea.left + horizontalInset, chartArea.right - horizontalInset);
                    y = clamp(pointY - radius - offset, chartArea.top + verticalInset, chartArea.bottom - verticalInset);

                    if (pointX > chartArea.right - horizontalInset) {
                        xAlign = 'right';
                    } else if (pointX < chartArea.left + horizontalInset) {
                        xAlign = 'left';
                    }
                } else if (preferLeftSide) {
                    x = clamp(pointX - radius - offset, chartArea.left + horizontalInset, chartArea.right - horizontalInset);
                    y = clamp(pointY, chartArea.top + verticalInset, chartArea.bottom - verticalInset);
                    xAlign = 'right';
                    yAlign = 'center';
                } else {
                    x = clamp(pointX + radius + offset, chartArea.left + horizontalInset, chartArea.right - horizontalInset);
                    y = clamp(pointY, chartArea.top + verticalInset, chartArea.bottom - verticalInset);
                    xAlign = 'left';
                    yAlign = 'center';
                }

                return {
                    x: x,
                    y: y,
                    xAlign: xAlign,
                    yAlign: yAlign
                };
            };
            riskBubbleTooltipPosition = 'riskBubbleSmartPosition';
        };

        feedbackConfig = feedbackConfig || {};

        if (!canvas || !filterEl || typeof Chart === 'undefined') {
            return null;
        }

        registerTooltipPositioner();

        var hideClusterList = function() {
            if (clusterListEl) {
                clusterListEl.hidden = true;
            }
            if (clusterListOptionsEl) {
                clusterListOptionsEl.innerHTML = '';
            }
        };

        var showClusterList = function(clusterPoint) {
            var members = (clusterPoint.members || []).slice().sort(function(a, b) {
                return Number(b.risk) - Number(a.risk);
            });

            currentSelectedClusterPoint = clusterPoint;
            setSelectionCard(null);
            setText(selectionNoteEl, members.length + ' students are clustered here. Choose a student to view details.');
            setText(selectionBadgeEl, members.length + ' students');
            setText(selectionZoneBadgeEl, 'Cluster');
            selectionBadgeEl.className = 'risk-bubble-badge is-medium';
            selectionZoneBadgeEl.className = 'risk-bubble-badge is-medium';
            if (clearSelectionEl) {
                clearSelectionEl.classList.add('is-visible');
            }

            if (!clusterListEl || !clusterListOptionsEl) {
                return;
            }

            setText(clusterListTitleEl, members.length + ' students in this cluster');
            clusterListOptionsEl.innerHTML = members.map(function(member) {
                return '<button type="button" class="risk-bubble-cluster-option" data-student-id="' +
                    escapeHtml(member.studentid) + '">' +
                    escapeHtml(member.student || 'Student ' + member.studentid) +
                    '<span>Risk ' + escapeHtml(Number(member.risk).toFixed(2)) + '</span>' +
                    '</button>';
            }).join('');
            clusterListEl.hidden = false;

            queryRegions(clusterListOptionsEl, '[data-student-id]').forEach(function(button) {
                button.addEventListener('click', function() {
                    var studentId = button.getAttribute('data-student-id');
                    var selectedMember = members.find(function(member) {
                        return String(member.studentid) === String(studentId);
                    });
                    var visibleIndex;

                    if (!selectedMember) {
                        return;
                    }

                    hideClusterList();
                    currentSelectedClusterPoint = null;
                    setSelectionCard(selectedMember);
                    if (clusterEl && clusterEl.checked) {
                        clusterEl.checked = false;
                    }
                    refreshChart();
                    visibleIndex = chart.data.datasets[0].data.findIndex(function(point) {
                        return String(point.studentid) === String(selectedMember.studentid);
                    });
                    chart.setActiveElements(visibleIndex === -1 ? [] : [{datasetIndex: 0, index: visibleIndex}]);
                    chart.update();
                    if (feedbackConfig.tableApi && typeof feedbackConfig.tableApi.setSelectedStudentId === 'function') {
                        feedbackConfig.tableApi.setSelectedStudentId(selectedMember.studentid);
                    }
                });
            });
        };

        var setSelectionCard = function(point) {
            var finalRiskZone;
            var chartZone;

            if (!point) {
                currentSelectedStudentId = null;
                currentSelectedPoint = null;
                setText(selectionNoteEl, 'Click a bubble to inspect a student.');
                setText(selectionBadgeEl, 'No selection');
                setText(selectionZoneBadgeEl, 'No zone');
                selectionBadgeEl.className = 'risk-bubble-badge';
                selectionZoneBadgeEl.className = 'risk-bubble-badge';
                if (clearSelectionEl) {
                    clearSelectionEl.classList.remove('is-visible');
                }
                setText(selectionStudentEl, 'Not selected');
                setText(selectionStudentIdEl, 'Not selected');
                setText(selectionEmailEl, 'Not selected');
                setText(selectionRiskEl, 'Not selected');
                setText(selectionBehaviourEl, 'Not selected');
                setText(selectionAcademicEl, 'Not selected');
                if (feedbackPanelEl) {
                    feedbackPanelEl.hidden = true;
                }
                if (feedbackStatusEl) {
                    feedbackStatusEl.textContent = '';
                }
                return;
            }

            hideClusterList();
            currentSelectedStudentId = point.studentid;
            currentSelectedPoint = point;
            finalRiskZone = getZoneConfig(point.risk);
            chartZone = getZoneConfig(point.y);

            setText(selectionNoteEl, 'Selected student details from the current chart view.');
            setText(selectionBadgeEl, finalRiskZone.finalLabel);
            setText(selectionZoneBadgeEl, chartZone.zoneLabel);
            selectionBadgeEl.className = 'risk-bubble-badge ' + finalRiskZone.badgeClass;
            selectionZoneBadgeEl.className = 'risk-bubble-badge ' + chartZone.badgeClass;
            if (clearSelectionEl) {
                clearSelectionEl.classList.add('is-visible');
            }
            setText(selectionStudentEl, point.student || 'N/A');
            setText(selectionStudentIdEl, point.studentid || 'N/A');
            setText(selectionEmailEl, point.email || 'N/A');
            setText(selectionRiskEl, point.risk.toFixed(2));
            setText(selectionBehaviourEl, point.x.toFixed(2));
            setText(selectionAcademicEl, point.y.toFixed(2));

            if (feedbackPanelEl) {
                feedbackPanelEl.hidden = false;
            }
            if (feedbackFormEl) {
                feedbackFormEl.reset();
            }
            if (feedbackPredictionIdEl) {
                feedbackPredictionIdEl.value = point.predictionid || '';
            }
            if (feedbackStudentKeyEl) {
                feedbackStudentKeyEl.value = point.studentid || '';
            }
            if (feedbackCourseKeyEl) {
                feedbackCourseKeyEl.value = point.coursekey || '';
            }
            if (feedbackSnapshotDateEl) {
                feedbackSnapshotDateEl.value = point.snapshotdate || '';
            }
            if (feedbackStatusEl) {
                feedbackStatusEl.textContent = '';
            }
        };

        var focusStudentById;
        var clearSelection;
        var resetFeedbackFormForPoint;

        resetFeedbackFormForPoint = function(point) {
            if (feedbackFormEl) {
                feedbackFormEl.reset();
            }
            if (!point) {
                return;
            }
            if (feedbackPredictionIdEl) {
                feedbackPredictionIdEl.value = point.predictionid || '';
            }
            if (feedbackStudentKeyEl) {
                feedbackStudentKeyEl.value = point.studentid || '';
            }
            if (feedbackCourseKeyEl) {
                feedbackCourseKeyEl.value = point.coursekey || '';
            }
            if (feedbackSnapshotDateEl) {
                feedbackSnapshotDateEl.value = point.snapshotdate || '';
            }
        };

        var updateFilterState = function() {
            topNControlEl.style.display = filterEl.value === 'top' ? 'flex' : 'none';
        };

        var getVisibleRange = function(axis) {
            var scaleOptions = chart && chart.options && chart.options.scales && chart.options.scales[axis];

            return {
                min: scaleOptions && typeof scaleOptions.min === 'number' ? scaleOptions.min : defaultScaleRange.min,
                max: scaleOptions && typeof scaleOptions.max === 'number' ? scaleOptions.max : defaultScaleRange.max
            };
        };

        var resetZoomRange = function() {
            if (!chart) {
                return;
            }
            if (typeof chart.resetZoom === 'function') {
                chart.resetZoom('none');
            }
            chart.options.scales.x.min = defaultScaleRange.min;
            chart.options.scales.x.max = defaultScaleRange.max;
            chart.options.scales.y.min = defaultScaleRange.min;
            chart.options.scales.y.max = defaultScaleRange.max;
            if (resetZoomEl) {
                resetZoomEl.hidden = true;
            }
        };

        var isUsableZoomRange = function() {
            var xRange = getVisibleRange('x');
            var yRange = getVisibleRange('y');

            return (xRange.max - xRange.min) >= RISK_BUBBLE_MIN_ZOOM_RANGE &&
                (yRange.max - yRange.min) >= RISK_BUBBLE_MIN_ZOOM_RANGE;
        };

        var withJitter = function(points, enabled) {
            return points.map(function(point) {
                var clone = {
                    x: point.x,
                    y: point.y,
                    r: point.r,
                    student: point.student,
                    studentid: point.studentid,
                    predictionid: point.predictionid,
                    coursekey: point.coursekey,
                    courselabel: point.courselabel,
                    snapshotdate: point.snapshotdate,
                    email: point.email,
                    risk: point.risk,
                    label: point.label
                };

                if (enabled) {
                    clone.x = clamp(point.x + (stableNoise(point.student, 'x') * 0.012), 0, 1);
                    clone.y = clamp(point.y + (stableNoise(point.student, 'y') * 0.012), 0, 1);
                }

                return clone;
            });
        };

        var filteredPoints = function() {
            var mode = filterEl.value;
            var topN = Number(topNEl.value);
            var minRisk = Number(thresholdEl.value);
            var sorted = bubblePoints.slice().sort(function(a, b) {
                return b.risk - a.risk;
            });
            var thresholdFiltered = sorted.filter(function(point) {
                return point.risk >= minRisk;
            });

            if (mode === 'atrisk') {
                thresholdFiltered = thresholdFiltered.filter(function(point) {
                    return Number(point.label) === 1;
                });
            } else if (mode === 'top') {
                thresholdFiltered = thresholdFiltered.slice(0, topN);
            }

            return withJitter(thresholdFiltered, jitterEl.checked);
        };

        var clusterPoints = function(points) {
            var xRange;
            var yRange;
            var xBucketSize;
            var yBucketSize;
            var groups = {};
            var clustered = [];

            if (!clusterEl || !clusterEl.checked || points.length < 2) {
                return points.map(function(point) {
                    point.isCluster = false;
                    return point;
                });
            }

            xRange = getVisibleRange('x');
            yRange = getVisibleRange('y');
            xBucketSize = Math.max((xRange.max - xRange.min) / 42, 0.006);
            yBucketSize = Math.max((yRange.max - yRange.min) / 42, 0.006);

            points.forEach(function(point) {
                var key = Math.floor((point.x - xRange.min) / xBucketSize) + ':' +
                    Math.floor((point.y - yRange.min) / yBucketSize);

                if (!groups[key]) {
                    groups[key] = [];
                }
                groups[key].push(point);
            });

            Object.keys(groups).forEach(function(key) {
                var members = groups[key];
                var clusterPoint;

                if (members.length === 1) {
                    members[0].isCluster = false;
                    clustered.push(members[0]);
                    return;
                }

                clusterPoint = {
                    x: members.reduce(function(sum, point) {
                        return sum + point.x;
                    }, 0) / members.length,
                    y: members.reduce(function(sum, point) {
                        return sum + point.y;
                    }, 0) / members.length,
                    r: clamp(8 + Math.sqrt(members.length) * 3.2, 10, 28),
                    student: members.length + ' students',
                    studentid: '',
                    predictionid: '',
                    coursekey: members[0].coursekey || '',
                    courselabel: members[0].courselabel || '',
                    snapshotdate: members[0].snapshotdate || '',
                    email: '',
                    risk: members.reduce(function(max, point) {
                        return Math.max(max, Number(point.risk) || 0);
                    }, 0),
                    label: members.some(function(point) {
                        return Number(point.label) === 1;
                    }) ? 1 : 0,
                    isCluster: true,
                    clusterCount: members.length,
                    members: members
                };
                clustered.push(clusterPoint);
            });

            return clustered;
        };

        var zonePlugin = {
            id: 'riskZoneBandsPlugin',
            beforeDraw: function(currentChart) {
                var chartArea = currentChart.chartArea;
                var yScale = currentChart.scales && currentChart.scales.y;
                var ctx;

                if (!chartArea || !yScale) {
                    return;
                }

                ctx = currentChart.ctx;
                ctx.save();

                riskZoneThresholds.forEach(function(zone) {
                    var top = yScale.getPixelForValue(zone.max);
                    var bottom = yScale.getPixelForValue(zone.min);
                    var height = bottom - top;

                    ctx.fillStyle = zone.chartColor;
                    ctx.fillRect(chartArea.left, top, chartArea.right - chartArea.left, height);
                    ctx.fillStyle = 'rgba(33, 37, 41, 0.65)';
                    ctx.font = '11px sans-serif';
                    ctx.fillText(zone.zoneLabel, chartArea.right - 90, top + 13);
                });

                ctx.restore();
            }
        };

        clearSelection = function() {
            currentSelectedStudentId = null;
            currentSelectedPoint = null;
            currentSelectedClusterPoint = null;
            hideClusterList();
            setSelectionCard(null);
            chart.setActiveElements([]);
            refreshChart();
            if (feedbackConfig.tableApi && typeof feedbackConfig.tableApi.clearSelectedStudentId === 'function') {
                feedbackConfig.tableApi.clearSelectedStudentId();
            }
        };

        chart = new Chart(canvas, {
            type: 'bubble',
            data: {
                datasets: [{
                    label: 'Students',
                    data: filteredPoints(),
                    backgroundColor: [],
                    borderColor: [],
                    borderWidth: 1.2,
                    hoverBorderWidth: 2,
                    hitRadius: 8
                }]
            },
            plugins: [zonePlugin],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        top: 12,
                        right: 12,
                        bottom: 12,
                        left: 12
                    }
                },
                scales: {
                    x: {
                        min: defaultScaleRange.min,
                        max: defaultScaleRange.max,
                        ticks: {
                            callback: formatPercentTick
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.08)'
                        },
                        title: {
                            display: true,
                            text: 'Behaviour Risk Score'
                        }
                    },
                    y: {
                        min: defaultScaleRange.min,
                        max: defaultScaleRange.max,
                        ticks: {
                            callback: formatPercentTick
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.08)'
                        },
                        title: {
                            display: true,
                            text: 'Academic Risk Score'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        position: riskBubbleTooltipPosition,
                        backgroundColor: 'rgba(255, 255, 255, 0.96)',
                        titleColor: '#0f172a',
                        bodyColor: '#64748b',
                        borderColor: 'rgba(148, 163, 184, 0.28)',
                        borderWidth: 1,
                        cornerRadius: 10,
                        padding: 10,
                        caretSize: 6,
                        displayColors: false,
                        titleFont: {
                            size: 12,
                            weight: '800'
                        },
                        bodyFont: {
                            size: 12,
                            weight: '600'
                        },
                        callbacks: {
                            title: function(context) {
                                var point = context[0] && context[0].raw;
                                if (!point) {
                                    return '';
                                }
                                if (point.isCluster) {
                                    return point.clusterCount + ' students clustered here';
                                }
                                return (point.student || 'Student') + ' | ID: ' + point.studentid;
                            },
                            labelTextColor: function(context) {
                                var point = context.raw;

                                if (!point) {
                                    return '#64748b';
                                }
                                if (point.isCluster) {
                                    return 'rgba(217, 119, 6, 1)';
                                }
                                return Number(point.label) === 1 ?
                                    'rgba(220, 53, 69, 1)' :
                                    'rgba(13, 110, 253, 1)';
                            },
                            label: function(context) {
                                var point = context.raw;
                                if (point.isCluster) {
                                    return 'Click to choose a student.';
                                }
                                return [
                                    'Final Risk: ' + point.risk.toFixed(2),
                                    'Behaviour: ' + point.x.toFixed(2) + '  Academic: ' + point.y.toFixed(2)
                                ];
                            }
                        }
                    },
                    zoom: {
                        limits: {
                            x: {min: defaultScaleRange.min, max: defaultScaleRange.max},
                            y: {min: defaultScaleRange.min, max: defaultScaleRange.max}
                        },
                        zoom: {
                            drag: {
                                enabled: true,
                                backgroundColor: 'rgba(13, 110, 253, 0.12)',
                                borderColor: 'rgba(13, 110, 253, 0.45)',
                                borderWidth: 1,
                                threshold: RISK_BUBBLE_ZOOM_DRAG_THRESHOLD
                            },
                            mode: 'xy',
                            onZoomComplete: function() {
                                if (!isUsableZoomRange()) {
                                    resetZoomRange();
                                    chart.update();
                                    return;
                                }
                                if (resetZoomEl) {
                                    resetZoomEl.hidden = false;
                                }
                                refreshChart();
                            }
                        }
                    }
                },
                onClick: function(event, elements) {
                    var selectedPoint;

                    if (!elements.length) {
                        clearSelection();
                        return;
                    }

                    selectedPoint = chart.data.datasets[0].data[elements[0].index];
                    if (selectedPoint.isCluster) {
                        showClusterList(selectedPoint);
                        refreshChart();
                        return;
                    }

                    currentSelectedClusterPoint = null;
                    setSelectionCard(selectedPoint);
                    refreshChart();
                }
            }
        });

        focusStudentById = function(studentId) {
            var target = bubblePoints.find(function(point) {
                return String(point.studentid) === String(studentId);
            });
            var visibleIndex;

            if (!target) {
                return false;
            }

            if (filterEl.value !== 'atrisk') {
                filterEl.value = 'atrisk';
            }

            if (Number(thresholdEl.value) > target.risk) {
                thresholdEl.value = String(target.risk.toFixed(2));
            }

            refreshChart();

            visibleIndex = chart.data.datasets[0].data.findIndex(function(point) {
                return String(point.studentid) === String(studentId);
            });

            if (visibleIndex === -1) {
                var containingCluster = chart.data.datasets[0].data.find(function(point) {
                    return point.isCluster && (point.members || []).some(function(member) {
                        return String(member.studentid) === String(studentId);
                    });
                });

                if (containingCluster && clusterEl && clusterEl.checked) {
                    clusterEl.checked = false;
                    refreshChart();
                    visibleIndex = chart.data.datasets[0].data.findIndex(function(point) {
                        return String(point.studentid) === String(studentId);
                    });
                }
            }

            if (visibleIndex === -1 && clusterEl && clusterEl.checked) {
                clusterEl.checked = false;
                refreshChart();
                visibleIndex = chart.data.datasets[0].data.findIndex(function(point) {
                    return String(point.studentid) === String(studentId);
                });
            }

            if (visibleIndex === -1) {
                return false;
            }

            currentSelectedClusterPoint = null;
            setSelectionCard(chart.data.datasets[0].data[visibleIndex]);
            refreshChart();
            return true;
        };

        var refreshChart = function() {
            var points = clusterPoints(filteredPoints());
            var dataset = chart.data.datasets[0];
            var selectedStudentId = currentSelectedStudentId;
            var selectedClusterPoint = currentSelectedClusterPoint;
            var activeIndex = -1;
            var hasSelection = !!selectedStudentId || !!selectedClusterPoint;
            var isSelectedChartPoint = function(point) {
                if (selectedStudentId) {
                    if (String(point.studentid) === String(selectedStudentId)) {
                        return true;
                    }
                    return point.isCluster && point.members && point.members.some(function(member) {
                        return String(member.studentid) === String(selectedStudentId);
                    });
                }
                if (!selectedClusterPoint) {
                    return false;
                }
                return point.isCluster && point.members && selectedClusterPoint.members &&
                    point.members.length === selectedClusterPoint.members.length &&
                    point.members.every(function(member) {
                        return selectedClusterPoint.members.some(function(selectedMember) {
                            return String(selectedMember.studentid) === String(member.studentid);
                        });
                    });
            };

            updateFilterState();
            dataset.data = points;
            dataset.backgroundColor = points.map(function(point) {
                var isSelected = isSelectedChartPoint(point);

                if (point.isCluster) {
                    return isSelected ? 'rgba(245, 158, 11, 0.72)' :
                        (hasSelection ? 'rgba(245, 158, 11, 0.20)' : 'rgba(245, 158, 11, 0.42)');
                }
                if (Number(point.label) === 1) {
                    return isSelected ? 'rgba(220, 53, 69, 0.72)' :
                        (hasSelection ? 'rgba(220, 53, 69, 0.16)' : 'rgba(220, 53, 69, 0.35)');
                }
                return isSelected ? 'rgba(13, 110, 253, 0.72)' :
                    (hasSelection ? 'rgba(13, 110, 253, 0.16)' : 'rgba(13, 110, 253, 0.35)');
            });
            dataset.borderColor = points.map(function(point) {
                var isSelected = isSelectedChartPoint(point);

                if (point.isCluster) {
                    return isSelected || !hasSelection ? 'rgba(217, 119, 6, 0.95)' : 'rgba(217, 119, 6, 0.34)';
                }
                if (Number(point.label) === 1) {
                    return isSelected || !hasSelection ? 'rgba(220, 53, 69, 0.95)' : 'rgba(220, 53, 69, 0.30)';
                }
                return isSelected || !hasSelection ? 'rgba(13, 110, 253, 0.95)' : 'rgba(13, 110, 253, 0.30)';
            });
            dataset.borderWidth = points.map(function(point) {
                return isSelectedChartPoint(point) ? 3 : 1.2;
            });
            setText(topNValueEl, topNEl.value);
            setText(thresholdValueEl, Number(thresholdEl.value).toFixed(2));
            if (selectedStudentId) {
                activeIndex = points.findIndex(function(point) {
                    return String(point.studentid) === String(selectedStudentId);
                });
                chart.setActiveElements(activeIndex === -1 ? [] : [{datasetIndex: 0, index: activeIndex}]);
            } else if (selectedClusterPoint) {
                activeIndex = points.findIndex(function(point) {
                    return point.isCluster && point.members && selectedClusterPoint.members &&
                        point.members.length === selectedClusterPoint.members.length &&
                        point.members.every(function(member) {
                            return selectedClusterPoint.members.some(function(selectedMember) {
                                return String(selectedMember.studentid) === String(member.studentid);
                            });
                        });
                });
                chart.setActiveElements(activeIndex === -1 ? [] : [{datasetIndex: 0, index: activeIndex}]);
            } else {
                setSelectionCard(null);
                chart.setActiveElements([]);
            }
            chart.update();
        };

        if (feedbackFormEl) {
            feedbackFormEl.addEventListener('submit', function(event) {
                var formData;

                event.preventDefault();

                if (!currentSelectedPoint) {
                    setText(feedbackStatusEl, 'Select a student before saving feedback.');
                    return;
                }

                formData = new FormData(feedbackFormEl);

                if (feedbackConfig.sesskey && !formData.get('sesskey')) {
                    formData.append('sesskey', feedbackConfig.sesskey);
                }

                if (feedbackSubmitEl) {
                    feedbackSubmitEl.disabled = true;
                }
                setText(feedbackStatusEl, 'Saving feedback...');

                fetch(feedbackConfig.feedbackUrl, {
                    method: 'POST',
                    credentials: 'same-origin',
                    body: formData
                })
                    .then(function(response) {
                        if (!response.ok) {
                            throw new Error('Feedback save failed.');
                        }
                        return response.json();
                    })
                    .then(function(data) {
                        if (!data || !data.success) {
                            throw new Error('Feedback save failed.');
                        }
                        resetFeedbackFormForPoint(currentSelectedPoint);
                        setText(feedbackStatusEl, 'Feedback saved.');
                    })
                    .catch(function() {
                        setText(feedbackStatusEl, 'Feedback could not be saved. Please try again.');
                    })
                    .then(function() {
                        if (feedbackSubmitEl) {
                            feedbackSubmitEl.disabled = false;
                        }
                    });
            });
        }

        if (clearSelectionEl) {
            clearSelectionEl.addEventListener('click', clearSelection);
        }

        filterEl.addEventListener('change', refreshChart);
        topNEl.addEventListener('input', refreshChart);
        thresholdEl.addEventListener('input', refreshChart);
        jitterEl.addEventListener('change', refreshChart);
        if (clusterEl) {
            clusterEl.addEventListener('change', refreshChart);
        }
        if (resetZoomEl) {
            resetZoomEl.addEventListener('click', function() {
                resetZoomRange();
                refreshChart();
            });
        }
        if (mapResetEl) {
            mapResetEl.addEventListener('click', function() {
                filterEl.value = DEFAULT_RISK_BUBBLE_FILTER;
                topNEl.value = String(DEFAULT_RISK_BUBBLE_TOP_N);
                thresholdEl.value = currentRiskThreshold.toFixed(2);
                if (jitterEl) {
                    jitterEl.checked = true;
                }
                if (clusterEl) {
                    clusterEl.checked = true;
                }
                clearSelection();
                resetZoomRange();
                refreshChart();
            });
        }
        refreshChart();

        return {
            chart: chart,
            focusStudentById: focusStudentById,
            clearSelection: clearSelection,
            updatePoints: function(points) {
                bubblePoints = points || [];
                clearSelection();
                refreshChart();
            },
            applyCourseConfig: function(courseConfig) {
                currentRiskThreshold = courseConfig && !Number.isNaN(Number(courseConfig.riskThreshold)) ?
                    clamp(Number(courseConfig.riskThreshold), 0, 1) : DEFAULT_RISK_BUBBLE_THRESHOLD;
                thresholdEl.value = currentRiskThreshold.toFixed(2);
                setText(thresholdValueEl, currentRiskThreshold.toFixed(2));
                if (lowLmsNoteEl) {
                    lowLmsNoteEl.hidden = !courseConfig || courseConfig.teachingMode !== 'Low';
                }
            }
        };
    };

    var initUnitFilter = function(root, bubblePoints, defaultCourseKey, onChange) {
        var unitFilterEl = queryRegion(root, 'unit-filter');
        var courseKeys;
        var hasDefaultCourseKey;
        var selectedCourseKey;
        var selectedPoints;

        if (!unitFilterEl) {
            return null;
        }

        courseKeys = bubblePoints.map(function(point) {
            return point.coursekey || '';
        }).filter(function(courseKey, index, values) {
            return values.indexOf(courseKey) === index;
        }).sort(function(left, right) {
            if (!left) {
                return 1;
            }
            if (!right) {
                return -1;
            }
            return String(left).localeCompare(String(right), undefined, {numeric: true, sensitivity: 'base'});
        });

        courseKeys.forEach(function(courseKey) {
            var option = document.createElement('option');
            option.value = courseKey || '__missing__';
            option.textContent = getCourseLabel(courseKey, bubblePoints);
            unitFilterEl.appendChild(option);
        });

        unitFilterEl.disabled = courseKeys.length === 0;
        unitFilterEl.addEventListener('change', function() {
            var selectedValue = unitFilterEl.value;
            var selectedCourseKey = selectedValue === '__missing__' ? '' : selectedValue;
            var filteredPoints = selectedValue === '' ? [] : bubblePoints.filter(function(point) {
                return String(point.coursekey || '') === String(selectedCourseKey);
            });

            onChange(filteredPoints, selectedValue !== '', selectedCourseKey);
        });

        hasDefaultCourseKey = defaultCourseKey !== null && defaultCourseKey !== undefined && String(defaultCourseKey) !== '';
        selectedCourseKey = hasDefaultCourseKey ? String(defaultCourseKey) : '';
        if (hasDefaultCourseKey && courseKeys.indexOf(selectedCourseKey) !== -1) {
            unitFilterEl.value = selectedCourseKey;
            selectedPoints = bubblePoints.filter(function(point) {
                return String(point.coursekey || '') === selectedCourseKey;
            });
        } else if (hasDefaultCourseKey && selectedCourseKey === '' && courseKeys.indexOf('') !== -1) {
            unitFilterEl.value = '__missing__';
            selectedPoints = bubblePoints.filter(function(point) {
                return String(point.coursekey || '') === '';
            });
        } else {
            unitFilterEl.value = '';
            selectedPoints = [];
        }

        onChange(selectedPoints, unitFilterEl.value !== '', unitFilterEl.value === '__missing__' ? '' : unitFilterEl.value);

        return unitFilterEl;
    };

    var initCourseConfigPanel = function(root, config, onSave) {
        var toggleEl = queryRegion(root, 'course-config-toggle');
        var panelEl = queryRegion(root, 'course-config-panel');
        var closeEl = queryRegion(root, 'course-config-close');
        var formEl = queryRegion(root, 'course-config-form');
        var statusEl = queryRegion(root, 'course-config-status');
        var saveEl = queryRegion(root, 'course-config-save');
        var courseLabelEl = queryRegion(root, 'course-config-course-label');
        var courseKeyEl = queryRegion(root, 'course-config-course-key');
        var courseLabelInputEl = queryRegion(root, 'course-config-course-label-input');
        var teachingModeEl = queryRegion(root, 'course-config-teaching-mode');
        var week1El = queryRegion(root, 'course-config-week1');
        var week2El = queryRegion(root, 'course-config-week2');
        var week3El = queryRegion(root, 'course-config-week3');
        var thresholdEl = queryRegion(root, 'course-config-risk-threshold');
        var newHighRiskEl = queryRegion(root, 'course-config-new-high-risk');
        var noLmsEl = queryRegion(root, 'course-config-no-lms');
        var frequencyEl = queryRegion(root, 'course-config-frequency');
        var selectedCourseKey = '';
        var selectedCourseLabel = '';
        var currentConfig;

        if (!toggleEl || !panelEl || !formEl) {
            return null;
        }

        var fillForm = function(courseConfig) {
            var engagement = courseConfig.earlyEngagementNotifications || {};
            var notificationTypes = courseConfig.notificationTypes || {};

            currentConfig = courseConfig;
            if (courseKeyEl) {
                courseKeyEl.value = courseConfig.courseKey || '';
            }
            if (courseLabelInputEl) {
                courseLabelInputEl.value = courseConfig.courseLabel || '';
            }
            setText(courseLabelEl, (courseConfig.courseLabel || 'Selected unit') +
                (courseConfig.isConfigured ? ' settings' : ' default settings'));
            if (teachingModeEl) {
                teachingModeEl.value = courseConfig.teachingMode || DEFAULT_COURSE_CONFIG.teachingMode;
            }
            if (week1El) {
                week1El.checked = !!engagement.week1;
            }
            if (week2El) {
                week2El.checked = !!engagement.week2;
            }
            if (week3El) {
                week3El.checked = !!engagement.week3;
            }
            if (thresholdEl) {
                thresholdEl.value = Number(courseConfig.riskThreshold).toFixed(2);
            }
            if (newHighRiskEl) {
                newHighRiskEl.checked = !!notificationTypes.newHighRisk;
            }
            if (noLmsEl) {
                noLmsEl.checked = !!notificationTypes.noLmsActivity;
            }
            if (frequencyEl) {
                frequencyEl.value = courseConfig.notificationFrequency || DEFAULT_COURSE_CONFIG.notificationFrequency;
            }
            if (statusEl) {
                statusEl.classList.remove('is-success');
            }
            setText(statusEl, courseConfig.isConfigured ? 'Saved configuration loaded.' : 'Using default configuration until saved.');
        };

        var setSelectedCourse = function(courseKey, courseLabel) {
            selectedCourseKey = courseKey || '';
            selectedCourseLabel = courseLabel || '';
            toggleEl.disabled = selectedCourseKey === '';

            if (!selectedCourseKey) {
                panelEl.hidden = true;
                setText(statusEl, '');
                return;
            }

            fillForm(getCourseConfig(config.courseConfigs, selectedCourseKey, selectedCourseLabel));
        };

        toggleEl.addEventListener('click', function() {
            if (!selectedCourseKey) {
                return;
            }
            panelEl.hidden = !panelEl.hidden;
            if (!panelEl.hidden) {
                fillForm(getCourseConfig(config.courseConfigs, selectedCourseKey, selectedCourseLabel));
            }
        });

        if (closeEl) {
            closeEl.addEventListener('click', function() {
                panelEl.hidden = true;
            });
        }

        formEl.addEventListener('submit', function(event) {
            var formData;

            event.preventDefault();
            if (!selectedCourseKey) {
                setText(statusEl, 'Select a unit before saving settings.');
                return;
            }

            formData = new FormData(formEl);
            if (config.sesskey && !formData.get('sesskey')) {
                formData.append('sesskey', config.sesskey);
            }

            if (saveEl) {
                saveEl.disabled = true;
            }
            setText(statusEl, 'Saving settings...');

            fetch(config.courseConfigUrl, {
                method: 'POST',
                credentials: 'same-origin',
                body: formData
            })
                .then(function(response) {
                    if (!response.ok) {
                        throw new Error('Settings save failed.');
                    }
                    return response.json();
                })
                .then(function(data) {
                    if (!data || !data.success || !data.config) {
                        throw new Error('Settings save failed.');
                    }
                    config.courseConfigs = config.courseConfigs || {};
                    config.courseConfigs[selectedCourseKey] = data.config;
                    fillForm(data.config);
                    if (statusEl) {
                        statusEl.classList.add('is-success');
                    }
                    setText(statusEl, 'Settings saved successfully.');
                    if (typeof onSave === 'function') {
                        onSave(data.config);
                    }
                })
                .catch(function() {
                    setText(statusEl, 'Settings could not be saved. Please try again.');
                })
                .then(function() {
                    if (saveEl) {
                        saveEl.disabled = false;
                    }
                });
        });

        return {
            setSelectedCourse: setSelectedCourse,
            getCurrentConfig: function() {
                return currentConfig;
            }
        };
    };

    window.blockSmartLmsDashboardInit = function(config) {
        var root = document.getElementById(config.rootId);
        var allBubblePoints = config.bubblePoints || [];
        var predictionMetadata = config.predictionMetadata || {};
        var refreshButtonEl;
        var tableApi;
        var bubbleApi;
        var distributionApi;
        var courseConfigApi;
        var refreshDashboard;
        var currentDashboardPoints = [];
        var currentDashboardHasSelectedUnit = false;
        var currentDashboardCourseKey = '';

        if (!root) {
            return;
        }

        if (root.getAttribute('data-dashboard-initialized') === 'true') {
            return;
        }

        if (typeof Chart === 'undefined') {
            window.setTimeout(function() {
                window.blockSmartLmsDashboardInit(config);
            }, 50);
            return;
        }

        root.setAttribute('data-dashboard-initialized', 'true');
        refreshButtonEl = queryRegion(root, 'dashboard-refresh');

        if (refreshButtonEl) {
            refreshButtonEl.addEventListener('click', function() {
                refreshButtonEl.disabled = true;
                refreshButtonEl.setAttribute('aria-label', 'Refreshing Smart LMS Dashboard');
                refreshButtonEl.setAttribute('title', 'Refreshing dashboard');
                window.location.reload();
            });
        }

        bubbleApi = initRiskBubble(root, allBubblePoints, {
            feedbackUrl: config.feedbackUrl,
            sesskey: config.sesskey,
            tableApi: {
                clearSelectedStudentId: function() {
                    if (tableApi && typeof tableApi.clearSelectedStudentId === 'function') {
                        tableApi.clearSelectedStudentId();
                    }
                },
                setSelectedStudentId: function(studentId) {
                    if (tableApi && typeof tableApi.setSelectedStudentId === 'function') {
                        tableApi.setSelectedStudentId(studentId);
                    }
                }
            }
        });

        tableApi = buildAtRiskTable(root, allBubblePoints, bubbleApi);
        distributionApi = initRiskDistribution(root, buildRiskDistributionFromPoints(allBubblePoints));
        courseConfigApi = initCourseConfigPanel(root, config, function() {
            refreshDashboard(currentDashboardPoints, currentDashboardHasSelectedUnit, currentDashboardCourseKey);
        });

        refreshDashboard = function(points, hasSelectedUnit, selectedCourseKey) {
            var distribution = buildRiskDistributionFromPoints(points);
            var courseLabel = selectedCourseKey ? getCourseLabel(selectedCourseKey, points.length ? points : allBubblePoints) : '';
            var courseConfig = selectedCourseKey ? getCourseConfig(config.courseConfigs, selectedCourseKey, courseLabel) :
                getCourseConfig(config.courseConfigs, '', '');

            currentDashboardPoints = points;
            currentDashboardHasSelectedUnit = hasSelectedUnit;
            currentDashboardCourseKey = selectedCourseKey || '';

            if (courseConfigApi && typeof courseConfigApi.setSelectedCourse === 'function') {
                courseConfigApi.setSelectedCourse(currentDashboardCourseKey, courseLabel);
            }
            if (bubbleApi && typeof bubbleApi.applyCourseConfig === 'function') {
                bubbleApi.applyCourseConfig(courseConfig);
            }
            if (bubbleApi && typeof bubbleApi.updatePoints === 'function') {
                bubbleApi.updatePoints(points);
            }
            if (tableApi && typeof tableApi.updatePoints === 'function') {
                tableApi.updatePoints(points);
            }
            if (distributionApi && typeof distributionApi.updateData === 'function') {
                distributionApi.updateData(distribution);
            }
            buildAiInsightSummary(root, distribution, points, predictionMetadata, hasSelectedUnit, courseConfig);
        };

        initUnitFilter(root, allBubblePoints, config.defaultCourseKey, refreshDashboard);
    };
})();
