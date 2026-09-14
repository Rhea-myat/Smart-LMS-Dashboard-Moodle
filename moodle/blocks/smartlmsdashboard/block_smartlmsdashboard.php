<?php
defined('MOODLE_INTERNAL') || die();

require_once(__DIR__ . '/classes/prediction_reader.php');

class block_smartlmsdashboard extends block_base {

    public function init() {
        $this->title = get_string('pluginname', 'block_smartlmsdashboard');
    }

    public function applicable_formats() {
        return ['all' => true];
    }

    public function instance_allow_multiple() {
        return false;
    }

    public function hide_header() {
        return true;
    }

    public function get_content() {
        if ($this->content !== null) {
            return $this->content;
        }

        $this->content = new stdClass();

        $context = !empty($this->context) ? $this->context : $this->page->context;
        $allowedcoursekeys = \block_smartlmsdashboard\prediction_reader::get_allowed_course_keys();
        $canview = has_capability('block/smartlmsdashboard:view', $context) ||
            \block_smartlmsdashboard\prediction_reader::user_can_view_all_units() ||
            ($allowedcoursekeys !== null && !empty($allowedcoursekeys));

        if (!$canview || ($allowedcoursekeys !== null && empty($allowedcoursekeys))) {
            $this->content->text = '';
            $this->content->footer = '';
            return $this->content;
        }

        $bubbledata = \block_smartlmsdashboard\prediction_reader::get_risk_bubble_data();
        $bubbledata = \block_smartlmsdashboard\prediction_reader::filter_points_by_course_access($bubbledata, $allowedcoursekeys);
        $riskdata = \block_smartlmsdashboard\prediction_reader::build_risk_distribution_from_points($bubbledata);
        $predictionmetadata = \block_smartlmsdashboard\prediction_reader::get_prediction_metadata();
        $courseconfigs = \block_smartlmsdashboard\prediction_reader::get_user_course_configs($bubbledata);
        $currentcourseid = null;

        if (!empty($this->page->context) && $this->page->context->contextlevel === CONTEXT_COURSE) {
            $currentcourseid = (int)$this->page->context->instanceid;
        } else if (!empty($this->page->course) && !empty($this->page->course->id)) {
            $currentcourseid = (int)$this->page->course->id;
        }

        $defaultcoursekey = \block_smartlmsdashboard\prediction_reader::get_default_course_key($currentcourseid);
        if ($allowedcoursekeys !== null && !in_array((string)$defaultcoursekey, array_map('strval', $allowedcoursekeys), true)) {
            $defaultcoursekey = $allowedcoursekeys[0] ?? null;
        }
        $rootid = 'smartlmsdashboard-' . $this->instance->id;

        $moduleconfig = [
            'rootId' => $rootid,
            'riskDistribution' => $riskdata,
            'bubblePoints' => $bubbledata,
            'predictionMetadata' => $predictionmetadata,
            'courseConfigs' => $courseconfigs,
            'defaultCourseKey' => $defaultcoursekey,
            'feedbackUrl' => (new moodle_url('/blocks/smartlmsdashboard/save_feedback.php'))->out(false),
            'courseConfigUrl' => (new moodle_url('/blocks/smartlmsdashboard/save_course_config.php'))->out(false),
            'sesskey' => sesskey(),
        ];

        $this->page->requires->js(new moodle_url('/blocks/smartlmsdashboard/js/dashboard.js', [
            'v' => filemtime(__DIR__ . '/js/dashboard.js'),
        ]));
        $this->page->requires->js_init_code('window.blockSmartLmsDashboardInit(' . json_encode($moduleconfig) . ');', true);

        $this->content->text = <<<HTML
<div id="{$rootid}" class="smartlmsdashboard-content">
    <style>
        .smartlmsdashboard-content .smartlmsdashboard-section-title {
            margin: 0 0 14px;
            font-size: 1.12rem;
            font-weight: 700;
            line-height: 1.3;
            letter-spacing: 0.01em;
            color: #0f172a;
        }

        .smartlmsdashboard-content {
            position: relative;
        }

        .smartlmsdashboard-content .smartlmsdashboard-header {
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: flex-start;
            margin-bottom: 16px;
        }

        .smartlmsdashboard-content .smartlmsdashboard-header-actions {
            display: grid;
            grid-template-columns: minmax(260px, 1fr) 38px;
            gap: 10px 14px;
            align-items: end;
            flex: 1 1 720px;
            max-width: 820px;
        }

        .smartlmsdashboard-content .smartlmsdashboard-icon-actions {
            display: flex;
            flex-direction: column;
            gap: 8px;
            align-items: center;
            justify-content: flex-start;
            grid-column: 2;
            grid-row: 1;
        }

        .smartlmsdashboard-content .smartlmsdashboard-course-config-toggle,
        .smartlmsdashboard-content .smartlmsdashboard-refresh {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 38px;
            height: 38px;
            padding: 0;
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 999px;
            background: #ffffff;
            color: #334155;
            cursor: pointer;
            transition: background 120ms ease, border-color 120ms ease, transform 120ms ease;
        }

        .smartlmsdashboard-content .smartlmsdashboard-course-config-toggle svg {
            width: 18px;
            height: 18px;
            stroke: currentColor;
        }

        .smartlmsdashboard-content .smartlmsdashboard-course-config-toggle:hover,
        .smartlmsdashboard-content .smartlmsdashboard-course-config-toggle:focus {
            background: #f8fafc;
            border-color: rgba(100, 116, 139, 0.45);
            color: #0f172a;
            transform: translateY(-1px);
        }

        .smartlmsdashboard-content .smartlmsdashboard-course-config-toggle[disabled] {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .smartlmsdashboard-content .smartlmsdashboard-title {
            margin: 0;
            font-size: 1.35rem;
            font-weight: 800;
            line-height: 1.2;
            color: #0f172a;
        }

        .smartlmsdashboard-content .smartlmsdashboard-unit-filter {
            display: flex;
            flex-direction: column;
            gap: 6px;
            min-width: 0;
            grid-column: 1;
            grid-row: 1;
        }

        .smartlmsdashboard-content .smartlmsdashboard-unit-filter label {
            font-size: 0.82rem;
            font-weight: 700;
            color: #475569;
        }

        .smartlmsdashboard-content .smartlmsdashboard-unit-filter select {
            width: 100%;
            padding: 9px 10px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 10px;
            background: #ffffff;
            color: #0f172a;
            font-size: 0.92rem;
        }

        .smartlmsdashboard-content .course-config-panel {
            margin: 0 0 16px;
            padding: 18px;
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 14px;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
        }

        .smartlmsdashboard-content .course-config-panel[hidden] {
            display: none;
        }

        .smartlmsdashboard-content .course-config-header {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: flex-start;
            margin-bottom: 14px;
        }

        .smartlmsdashboard-content .course-config-title {
            margin: 0;
            font-size: 1rem;
            font-weight: 800;
            color: #0f172a;
        }

        .smartlmsdashboard-content .course-config-subtitle {
            margin: 4px 0 0;
            font-size: 0.9rem;
            color: #64748b;
        }

        .smartlmsdashboard-content .course-config-close {
            border: 0;
            background: transparent;
            color: #64748b;
            font-size: 1.2rem;
            font-weight: 800;
            cursor: pointer;
            line-height: 1;
        }

        .smartlmsdashboard-content .course-config-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 18px 20px;
        }

        .smartlmsdashboard-content .course-config-field {
            display: flex;
            flex-direction: column;
            gap: 9px;
            min-width: 0;
            margin: 0;
            padding: 0;
            border: 0;
        }

        .smartlmsdashboard-content .course-config-field.is-wide {
            grid-column: span 2;
        }

        .smartlmsdashboard-content .course-config-field label,
        .smartlmsdashboard-content .course-config-legend {
            margin: 0;
            font-size: 0.82rem;
            font-weight: 800;
            color: #334155;
        }

        .smartlmsdashboard-content .course-config-label-row {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            min-width: 0;
        }

        .smartlmsdashboard-content .course-config-help {
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 auto;
            width: 18px;
            height: 18px;
            border: 1px solid rgba(100, 116, 139, 0.28);
            border-radius: 999px;
            background: #ffffff;
            color: #64748b;
            font-size: 0.76rem;
            font-weight: 800;
            line-height: 1;
            cursor: help;
        }

        .smartlmsdashboard-content .course-config-help::after {
            content: attr(data-tooltip);
            position: absolute;
            left: 50%;
            bottom: calc(100% + 8px);
            width: min(280px, 70vw);
            padding: 8px 10px;
            border-radius: 8px;
            background: #0f172a;
            color: #f8fafc;
            font-size: 0.78rem;
            font-weight: 500;
            line-height: 1.35;
            transform: translateX(-50%);
            opacity: 0;
            pointer-events: none;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
            transition: opacity 120ms ease;
            z-index: 10;
        }

        .smartlmsdashboard-content .course-config-help:hover::after,
        .smartlmsdashboard-content .course-config-help:focus::after {
            opacity: 1;
        }

        .smartlmsdashboard-content .course-config-field select,
        .smartlmsdashboard-content .course-config-field input[type="number"] {
            width: 100%;
            padding: 9px 10px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 10px;
            background: #ffffff;
            color: #0f172a;
            font-size: 0.92rem;
        }

        .smartlmsdashboard-content .course-config-note {
            margin: 0;
            font-size: 0.8rem;
            color: #64748b;
            line-height: 1.35;
        }

        .smartlmsdashboard-content .course-config-checks {
            display: grid;
            gap: 10px;
            margin-top: 2px;
        }

        .smartlmsdashboard-content .course-config-check {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9rem;
            color: #334155;
        }

        .smartlmsdashboard-content .course-config-check input.course-config-inline-input[type="number"] {
            width: 72px;
            min-width: 72px;
            padding: 6px 8px;
            margin: 0 6px;
        }

        .smartlmsdashboard-content .course-config-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-top: 14px;
        }

        .smartlmsdashboard-content .course-config-status {
            font-size: 0.86rem;
            color: #64748b;
        }

        .smartlmsdashboard-content .course-config-status.is-success {
            color: #15803d;
            font-weight: 800;
        }

        .smartlmsdashboard-content .course-config-save {
            padding: 9px 14px;
            border: 0;
            border-radius: 10px;
            background: #0f172a;
            color: #ffffff;
            font-size: 0.9rem;
            font-weight: 800;
            cursor: pointer;
        }

        .smartlmsdashboard-content .course-config-save[disabled] {
            opacity: 0.62;
            cursor: wait;
        }

        .smartlmsdashboard-content .smartlmsdashboard-refresh {
            grid-column: 2;
            grid-row: 1;
        }

        .smartlmsdashboard-content .smartlmsdashboard-refresh svg {
            width: 18px;
            height: 18px;
            stroke: currentColor;
        }

        .smartlmsdashboard-content .smartlmsdashboard-refresh:hover {
            background: #f8fafc;
            border-color: rgba(100, 116, 139, 0.45);
            transform: translateY(-1px);
        }

        .smartlmsdashboard-content .smartlmsdashboard-refresh[disabled] {
            opacity: 0.6;
            cursor: wait;
            transform: none;
        }

        .smartlmsdashboard-content .smartlmsdashboard-refresh[disabled] svg {
            animation: smartlmsdashboard-spin 900ms linear infinite;
        }

        @keyframes smartlmsdashboard-spin {
            from {
                transform: rotate(0deg);
            }
            to {
                transform: rotate(360deg);
            }
        }

        .smartlmsdashboard-content .predictive-analytics-block {
            padding: 18px;
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 14px;
            background: #ffffff;
        }

        .smartlmsdashboard-content .predictive-analytics-header {
            margin-bottom: 16px;
        }

        .smartlmsdashboard-content .predictive-analytics-title {
            margin: 0 0 4px;
            font-size: 1.22rem;
            font-weight: 800;
            color: #0f172a;
        }

        .smartlmsdashboard-content .predictive-analytics-subtitle {
            margin: 0;
            font-size: 0.94rem;
            color: #64748b;
        }

        .smartlmsdashboard-content .risk-distribution-shell {
            display: grid;
            grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.9fr);
            gap: 16px;
            margin: 0 0 18px;
            align-items: stretch;
        }

        .smartlmsdashboard-content .risk-distribution-card,
        .smartlmsdashboard-content .risk-distribution-summary,
        .smartlmsdashboard-content .risk-bubble-selection-card,
        .smartlmsdashboard-content .risk-bubble-table-card,
        .smartlmsdashboard-content .ai-insight-summary {
            padding: 16px;
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 14px;
            background: linear-gradient(180deg, #fbfcfd 0%, #f8fafc 100%);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
        }

        .smartlmsdashboard-content .risk-distribution-card {
            min-width: 0;
        }

        .smartlmsdashboard-content .risk-distribution-chart-wrap {
            height: 260px;
            position: relative;
        }

        .smartlmsdashboard-content .risk-distribution-tooltip {
            position: absolute;
            z-index: 4;
            min-width: 118px;
            padding: 8px 10px;
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.96);
            color: #0f172a;
            box-shadow: 0 12px 26px rgba(15, 23, 42, 0.14);
            pointer-events: none;
            opacity: 0;
            transform: translate(-50%, -100%);
            transition: opacity 100ms ease;
        }

        .smartlmsdashboard-content .risk-distribution-tooltip-count {
            display: block;
            font-size: 0.9rem;
            font-weight: 800;
            line-height: 1.25;
        }

        .smartlmsdashboard-content .risk-distribution-tooltip-rate {
            display: block;
            margin-top: 2px;
            font-size: 0.8rem;
            font-weight: 600;
            color: #64748b;
            line-height: 1.25;
        }

        .smartlmsdashboard-content .risk-distribution-summary {
            display: flex;
            flex-direction: column;
            gap: 12px;
            justify-content: center;
        }

        .smartlmsdashboard-content .risk-summary-heading,
        .smartlmsdashboard-content .risk-bubble-selection-title {
            margin: 0;
            font-size: 1rem;
            font-weight: 700;
            color: #0f172a;
        }

        .smartlmsdashboard-content .risk-summary-subtext,
        .smartlmsdashboard-content .risk-bubble-selection-note,
        .smartlmsdashboard-content .risk-bubble-table-note {
            margin: 6px 0 0;
            font-size: 0.92rem;
            color: #64748b;
        }

        .smartlmsdashboard-content .risk-summary-stat-grid,
        .smartlmsdashboard-content .risk-bubble-selection-grid {
            display: grid;
            gap: 12px;
        }

        .smartlmsdashboard-content .risk-summary-stat-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }

        .smartlmsdashboard-content .risk-summary-stat {
            width: 100%;
            padding: 12px;
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: #ffffff;
            cursor: pointer;
            transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
            appearance: none;
            text-align: left;
            font: inherit;
        }

        .smartlmsdashboard-content .risk-summary-stat:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
        }

        .smartlmsdashboard-content .risk-summary-stat.is-blue {
            background: linear-gradient(180deg, rgba(13, 110, 253, 0.08) 0%, rgba(255, 255, 255, 1) 100%);
        }

        .smartlmsdashboard-content .risk-summary-stat.is-red {
            background: linear-gradient(180deg, rgba(220, 53, 69, 0.08) 0%, rgba(255, 255, 255, 1) 100%);
        }

        .smartlmsdashboard-content .risk-summary-stat.is-active {
            border-color: rgba(15, 23, 42, 0.24);
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.12);
            transform: translateY(-1px);
        }

        .smartlmsdashboard-content .risk-summary-stat-label,
        .smartlmsdashboard-content .risk-bubble-selection-label {
            display: block;
            margin-bottom: 6px;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-transform: uppercase;
            color: #64748b;
        }

        .smartlmsdashboard-content .risk-summary-stat-value,
        .smartlmsdashboard-content .risk-bubble-selection-value {
            display: block;
            font-size: 1.05rem;
            font-weight: 700;
            color: #0f172a;
            word-break: break-word;
        }

        .smartlmsdashboard-content .risk-summary-highlight {
            padding: 12px 14px;
            border-radius: 12px;
            background: #0f172a;
            color: #f8fafc;
        }

        .smartlmsdashboard-content .risk-summary-highlight-label {
            display: block;
            margin-bottom: 4px;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-transform: uppercase;
            color: rgba(248, 250, 252, 0.76);
        }

        .smartlmsdashboard-content .risk-summary-highlight-value {
            font-size: 1.5rem;
            font-weight: 700;
        }

        .smartlmsdashboard-content .risk-bubble-toolbar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin: 8px 0 16px;
            padding: 14px;
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 12px;
            background: linear-gradient(180deg, #fbfcfd 0%, #f4f7fa 100%);
        }

        .smartlmsdashboard-content .risk-bubble-map-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-top: 18px;
        }

        .smartlmsdashboard-content .risk-bubble-map-header .smartlmsdashboard-section-title {
            margin: 0;
        }

        .smartlmsdashboard-content .risk-bubble-map-reset {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 auto;
            width: 32px;
            height: 32px;
            padding: 0;
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 999px;
            background: #ffffff;
            color: #334155;
            cursor: pointer;
            transition: background 120ms ease, border-color 120ms ease, transform 120ms ease;
        }

        .smartlmsdashboard-content .risk-bubble-map-reset svg {
            width: 16px;
            height: 16px;
            stroke: currentColor;
        }

        .smartlmsdashboard-content .risk-bubble-map-reset:hover,
        .smartlmsdashboard-content .risk-bubble-map-reset:focus {
            background: #f8fafc;
            border-color: rgba(100, 116, 139, 0.45);
            color: #0f172a;
            transform: translateY(-1px);
        }

        .smartlmsdashboard-content .risk-bubble-context-note {
            margin: 8px 0 12px;
            padding: 10px 12px;
            border: 1px solid rgba(245, 158, 11, 0.24);
            border-radius: 10px;
            background: rgba(245, 158, 11, 0.08);
            color: #92400e;
            font-size: 0.88rem;
            font-weight: 700;
            line-height: 1.4;
        }

        .smartlmsdashboard-content .risk-bubble-context-note[hidden] {
            display: none;
        }

        .smartlmsdashboard-content .risk-bubble-control {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .smartlmsdashboard-content .risk-bubble-control label {
            margin: 0;
            font-size: 0.9rem;
            font-weight: 600;
            color: #334155;
        }

        .smartlmsdashboard-content .risk-bubble-control select,
        .smartlmsdashboard-content .risk-bubble-control input[type="range"] {
            width: 100%;
        }

        .smartlmsdashboard-content .risk-bubble-value {
            font-size: 0.88rem;
            color: #475569;
        }

        .smartlmsdashboard-content .risk-bubble-toggle-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
        }

        .smartlmsdashboard-content .risk-bubble-toggle {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 10px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.85);
            border: 1px solid rgba(0, 0, 0, 0.06);
            font-size: 0.9rem;
            color: #334155;
        }

        .smartlmsdashboard-content .risk-bubble-chart-actions {
            display: flex;
            justify-content: flex-end;
            margin: -4px 0 10px;
        }

        .smartlmsdashboard-content .risk-bubble-action-button {
            padding: 8px 10px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 10px;
            background: #ffffff;
            color: #0f172a;
            font-size: 0.86rem;
            font-weight: 700;
            cursor: pointer;
        }

        .smartlmsdashboard-content .risk-bubble-action-button[hidden] {
            display: none;
        }

        .smartlmsdashboard-content .risk-bubble-tooltip {
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 18px;
            height: 18px;
            border-radius: 999px;
            border: 1px solid rgba(100, 116, 139, 0.28);
            background: #ffffff;
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 700;
            line-height: 1;
            cursor: help;
        }

        .smartlmsdashboard-content .risk-bubble-tooltip::after {
            content: attr(data-tooltip);
            position: absolute;
            left: 50%;
            bottom: calc(100% + 8px);
            width: min(260px, 70vw);
            padding: 8px 10px;
            border-radius: 8px;
            background: #0f172a;
            color: #f8fafc;
            font-size: 0.78rem;
            font-weight: 500;
            line-height: 1.35;
            text-transform: none;
            transform: translateX(-50%);
            opacity: 0;
            pointer-events: none;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
            transition: opacity 120ms ease;
            z-index: 5;
        }

        .smartlmsdashboard-content .risk-bubble-tooltip:hover::after,
        .smartlmsdashboard-content .risk-bubble-tooltip:focus::after {
            opacity: 1;
        }

        .smartlmsdashboard-content .risk-bubble-chart-wrap {
            height: 320px;
            max-width: 100%;
        }

        .smartlmsdashboard-content .risk-bubble-selection-card {
            margin-top: 14px;
            background: #ffffff;
        }

        .smartlmsdashboard-content .risk-bubble-selection-grid {
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        }

        .smartlmsdashboard-content .risk-bubble-selection-header {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: flex-start;
            margin-bottom: 10px;
        }

        .smartlmsdashboard-content .risk-bubble-selection-title-wrap {
            min-width: 0;
        }

        .smartlmsdashboard-content .risk-bubble-clear-selection {
            display: none;
            padding: 8px 10px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 10px;
            background: #ffffff;
            color: #0f172a;
            font-size: 0.86rem;
            font-weight: 700;
            cursor: pointer;
        }

        .smartlmsdashboard-content .risk-bubble-clear-selection.is-visible {
            display: inline-flex;
        }

        .smartlmsdashboard-content .risk-bubble-badge-stack {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 8px;
        }

        .smartlmsdashboard-content .risk-bubble-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 120px;
            padding: 8px 12px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-transform: uppercase;
            color: #fff;
            background: #64748b;
            box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.18);
        }

        .smartlmsdashboard-content .risk-bubble-badge.is-low {
            background: linear-gradient(135deg, #15803d 0%, #16a34a 100%);
        }

        .smartlmsdashboard-content .risk-bubble-badge.is-medium {
            background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%);
        }

        .smartlmsdashboard-content .risk-bubble-badge.is-high {
            background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
        }

        .smartlmsdashboard-content .risk-bubble-selection-item {
            padding: 10px 12px;
            border-radius: 10px;
            background: #f8fafc;
            border: 1px solid rgba(148, 163, 184, 0.2);
        }

        .smartlmsdashboard-content .risk-bubble-cluster-list {
            margin-top: 12px;
            padding: 12px;
            border: 1px solid rgba(245, 158, 11, 0.24);
            border-radius: 12px;
            background: rgba(245, 158, 11, 0.08);
        }

        .smartlmsdashboard-content .risk-bubble-cluster-list[hidden] {
            display: none;
        }

        .smartlmsdashboard-content .risk-bubble-cluster-title {
            margin: 0 0 8px;
            font-size: 0.9rem;
            font-weight: 700;
            color: #92400e;
        }

        .smartlmsdashboard-content .risk-bubble-cluster-options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 8px;
        }

        .smartlmsdashboard-content .risk-bubble-cluster-option {
            display: flex;
            justify-content: space-between;
            gap: 8px;
            align-items: center;
            padding: 9px 10px;
            border: 1px solid rgba(245, 158, 11, 0.28);
            border-radius: 10px;
            background: #ffffff;
            color: #0f172a;
            font-size: 0.88rem;
            font-weight: 700;
            text-align: left;
            cursor: pointer;
        }

        .smartlmsdashboard-content .risk-bubble-cluster-option span {
            font-weight: 600;
            color: #64748b;
        }

        .smartlmsdashboard-content .uc-feedback-panel {
            margin-top: 14px;
            padding: 14px;
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 12px;
            background: #f8fafc;
        }

        .smartlmsdashboard-content .uc-feedback-panel[hidden] {
            display: none;
        }

        .smartlmsdashboard-content .uc-feedback-title {
            margin: 0 0 4px;
            font-size: 0.98rem;
            font-weight: 700;
            color: #0f172a;
        }

        .smartlmsdashboard-content .uc-feedback-header {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            margin-bottom: 12px;
        }

        .smartlmsdashboard-content .uc-feedback-heading {
            min-width: 0;
        }

        .smartlmsdashboard-content .uc-feedback-note,
        .smartlmsdashboard-content .uc-feedback-status {
            margin: 0 0 12px;
            font-size: 0.88rem;
            color: #64748b;
        }

        .smartlmsdashboard-content .uc-feedback-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
        }

        .smartlmsdashboard-content .uc-feedback-field {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .smartlmsdashboard-content .uc-feedback-field label,
        .smartlmsdashboard-content .uc-feedback-legend {
            margin: 0;
            font-size: 0.84rem;
            font-weight: 700;
            color: #334155;
        }

        .smartlmsdashboard-content .uc-feedback-field select,
        .smartlmsdashboard-content .uc-feedback-field textarea {
            width: 100%;
            padding: 9px 10px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 10px;
            background: #ffffff;
            color: #0f172a;
            font-size: 0.92rem;
        }

        .smartlmsdashboard-content .uc-feedback-field textarea {
            min-height: 84px;
            resize: vertical;
        }

        .smartlmsdashboard-content .uc-feedback-reason-field {
            margin-top: 16px;
        }

        .smartlmsdashboard-content .uc-feedback-comments-field {
            margin-top: 14px;
        }

        .smartlmsdashboard-content .uc-feedback-reasons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 10px 12px;
            margin: 8px 0 0;
        }

        .smartlmsdashboard-content .uc-feedback-checkbox {
            display: flex;
            gap: 8px;
            align-items: flex-start;
            font-size: 0.9rem;
            color: #334155;
        }

        .smartlmsdashboard-content .uc-feedback-actions {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            align-items: center;
            margin-top: 12px;
        }

        .smartlmsdashboard-content .uc-feedback-submit-group {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            align-items: center;
            margin-left: auto;
        }

        .smartlmsdashboard-content .uc-feedback-submit {
            padding: 9px 14px;
            border: 1px solid rgba(13, 110, 253, 0.45);
            border-radius: 10px;
            background: #0d6efd;
            color: #ffffff;
            font-size: 0.9rem;
            font-weight: 700;
            cursor: pointer;
        }

        .smartlmsdashboard-content .uc-feedback-submit[disabled] {
            opacity: 0.58;
            cursor: not-allowed;
        }

        .smartlmsdashboard-content .risk-bubble-table-card {
            margin-top: 14px;
        }

        .smartlmsdashboard-content .risk-bubble-table-card summary {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 700;
            color: #0f172a;
            list-style: none;
        }

        .smartlmsdashboard-content .risk-bubble-table-card summary::-webkit-details-marker {
            display: none;
        }

        .smartlmsdashboard-content .risk-bubble-table-count {
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(220, 53, 69, 0.1);
            color: #b91c1c;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .smartlmsdashboard-content .risk-bubble-table-wrap {
            margin-top: 14px;
            overflow-x: auto;
        }

        .smartlmsdashboard-content .risk-bubble-table-toolbar {
            display: grid;
            grid-template-columns: minmax(220px, 1.2fr) repeat(2, minmax(160px, 0.7fr)) auto;
            gap: 10px;
            margin-top: 14px;
            align-items: end;
        }

        .smartlmsdashboard-content .risk-bubble-table-control {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .smartlmsdashboard-content .risk-bubble-table-control label,
        .smartlmsdashboard-content .risk-bubble-pagination-status {
            font-size: 0.82rem;
            font-weight: 600;
            color: #475569;
        }

        .smartlmsdashboard-content .risk-bubble-table-control input,
        .smartlmsdashboard-content .risk-bubble-table-control select {
            width: 100%;
            padding: 9px 10px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 10px;
            background: #ffffff;
            color: #0f172a;
            font-size: 0.92rem;
        }

        .smartlmsdashboard-content .risk-bubble-table-actions {
            display: flex;
            justify-content: flex-end;
        }

        .smartlmsdashboard-content .risk-bubble-table-button,
        .smartlmsdashboard-content .risk-bubble-pagination button {
            padding: 9px 12px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 10px;
            background: #ffffff;
            color: #0f172a;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 120ms ease, border-color 120ms ease, transform 120ms ease;
        }

        .smartlmsdashboard-content .risk-bubble-table-button:hover,
        .smartlmsdashboard-content .risk-bubble-pagination button:hover {
            background: #f8fafc;
            border-color: rgba(100, 116, 139, 0.45);
            transform: translateY(-1px);
        }

        .smartlmsdashboard-content .risk-bubble-table th button {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 0;
            border: 0;
            background: transparent;
            color: inherit;
            font: inherit;
            cursor: pointer;
        }

        .smartlmsdashboard-content .risk-bubble-table tbody tr {
            cursor: pointer;
        }

        .smartlmsdashboard-content .risk-bubble-table {
            width: 100%;
            border-collapse: collapse;
            min-width: 720px;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
        }

        .smartlmsdashboard-content .risk-bubble-table th,
        .smartlmsdashboard-content .risk-bubble-table td {
            padding: 12px 14px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.16);
            text-align: left;
            font-size: 0.92rem;
            color: #1e293b;
            vertical-align: top;
        }

        .smartlmsdashboard-content .risk-bubble-table th {
            background: #f8fafc;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-transform: uppercase;
            color: #64748b;
        }

        .smartlmsdashboard-content .risk-bubble-table tbody tr:hover {
            background: rgba(13, 110, 253, 0.04);
        }

        .smartlmsdashboard-content .risk-bubble-table tbody tr.is-selected {
            background: rgba(13, 110, 253, 0.1);
            box-shadow: inset 3px 0 0 rgba(13, 110, 253, 0.95);
        }

        .smartlmsdashboard-content .risk-bubble-pagination {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            gap: 10px;
            align-items: center;
            margin-top: 12px;
        }

        .smartlmsdashboard-content .risk-bubble-pagination-controls {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .smartlmsdashboard-content .risk-bubble-pagination button[disabled] {
            opacity: 0.45;
            cursor: not-allowed;
            transform: none;
        }

        .smartlmsdashboard-content .ai-insight-summary {
            margin-top: 16px;
            background: #ffffff;
        }

        .smartlmsdashboard-content .ai-insight-header {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: flex-start;
            margin-bottom: 14px;
        }

        .smartlmsdashboard-content .ai-insight-title {
            margin: 0;
            font-size: 1.04rem;
            font-weight: 700;
            color: #0f172a;
        }

        .smartlmsdashboard-content .ai-insight-subtitle {
            margin: 6px 0 0;
            font-size: 0.92rem;
            color: #64748b;
        }

        .smartlmsdashboard-content .ai-insight-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-bottom: 14px;
        }

        .smartlmsdashboard-content .prediction-info-footer {
            margin-top: 16px;
            padding-top: 12px;
            border-top: 1px solid rgba(148, 163, 184, 0.22);
        }

        .smartlmsdashboard-content .prediction-info-footer-title {
            margin: 0 0 8px;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-transform: uppercase;
            color: #64748b;
        }

        .smartlmsdashboard-content .ai-insight-metadata-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 10px;
        }

        .smartlmsdashboard-content .ai-insight-card {
            padding: 12px;
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 12px;
            background: #f8fafc;
        }

        .smartlmsdashboard-content .ai-insight-meta-card {
            display: flex;
            flex-wrap: wrap;
            gap: 4px 6px;
            align-items: baseline;
            min-width: 0;
        }

        .smartlmsdashboard-content .ai-insight-card-label {
            display: block;
            margin-bottom: 6px;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-transform: uppercase;
            color: #64748b;
        }

        .smartlmsdashboard-content .ai-insight-card-value {
            display: block;
            font-size: 1rem;
            font-weight: 700;
            color: #0f172a;
        }

        .smartlmsdashboard-content .ai-insight-meta-label,
        .smartlmsdashboard-content .ai-insight-meta-value {
            font-size: 0.82rem;
            line-height: 1.35;
            color: #64748b;
        }

        .smartlmsdashboard-content .ai-insight-meta-label {
            font-weight: 700;
        }

        .smartlmsdashboard-content .ai-insight-meta-value {
            font-weight: 600;
        }

        .smartlmsdashboard-content .ai-insight-copy {
            display: grid;
            gap: 12px;
        }

        .smartlmsdashboard-content .ai-insight-copy-block {
            padding: 12px 14px;
            border-left: 4px solid rgba(13, 110, 253, 0.72);
            background: rgba(13, 110, 253, 0.05);
            border-radius: 10px;
        }

        .smartlmsdashboard-content .ai-insight-copy-block.is-finding {
            border-left-color: rgba(245, 158, 11, 0.72);
            background: rgba(245, 158, 11, 0.08);
        }

        .smartlmsdashboard-content .ai-insight-copy-block.is-action {
            border-left-color: rgba(22, 163, 74, 0.72);
            background: rgba(22, 163, 74, 0.08);
        }

        .smartlmsdashboard-content .ai-insight-copy-title {
            margin: 0 0 6px;
            font-size: 0.9rem;
            font-weight: 700;
            color: #0f172a;
        }

        .smartlmsdashboard-content .ai-insight-copy-text {
            margin: 0;
            font-size: 0.92rem;
            line-height: 1.5;
            color: #334155;
        }

        .smartlmsdashboard-content .ai-insight-list {
            margin: 0;
            padding-left: 18px;
            font-size: 0.92rem;
            line-height: 1.5;
            color: #334155;
        }

        .smartlmsdashboard-content .ai-insight-list li + li {
            margin-top: 6px;
        }

        @media (max-width: 900px) {
            .smartlmsdashboard-content .risk-distribution-shell {
                grid-template-columns: 1fr;
            }

            .smartlmsdashboard-content .risk-bubble-table-toolbar {
                grid-template-columns: 1fr;
            }

            .smartlmsdashboard-content .risk-bubble-table-actions {
                justify-content: stretch;
            }

            .smartlmsdashboard-content .risk-bubble-table-button {
                width: 100%;
            }

            .smartlmsdashboard-content .uc-feedback-actions {
                display: block;
            }

            .smartlmsdashboard-content .smartlmsdashboard-header {
                display: block;
            }

            .smartlmsdashboard-content .smartlmsdashboard-header-actions {
                display: grid;
                grid-template-columns: minmax(0, 1fr) 38px;
                width: 100%;
                max-width: none;
                margin-top: 14px;
            }

            .smartlmsdashboard-content .smartlmsdashboard-unit-filter,
            .smartlmsdashboard-content .uc-feedback-submit-group {
                margin-top: 0;
            }

            .smartlmsdashboard-content .ai-insight-header {
                display: block;
            }

            .smartlmsdashboard-content .ai-insight-grid {
                grid-template-columns: 1fr;
            }

            .smartlmsdashboard-content .course-config-grid {
                grid-template-columns: 1fr;
            }

        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2"></script>

    <div class="smartlmsdashboard-header">
        <h2 class="smartlmsdashboard-title">Smart LMS Dashboard</h2>
        <div class="smartlmsdashboard-header-actions">
            <div class="smartlmsdashboard-unit-filter">
                <label for="{$rootid}-unit-filter">Unit</label>
                <select id="{$rootid}-unit-filter" data-region="unit-filter">
                    <option value="">Select a unit</option>
                </select>
            </div>
            <div class="smartlmsdashboard-icon-actions">
                <button type="button" class="smartlmsdashboard-refresh" data-region="dashboard-refresh" aria-label="Refresh Smart LMS Dashboard" title="Refresh dashboard">
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 12a9 9 0 1 1-2.64-6.36"></path>
                        <path d="M21 3v6h-6"></path>
                    </svg>
                </button>
                <button type="button" class="smartlmsdashboard-course-config-toggle" data-region="course-config-toggle" aria-label="Configure selected unit" title="Configure selected unit" disabled>
                    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                        <path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.06.06a2.1 2.1 0 1 1-2.97 2.97l-.06-.06a1.8 1.8 0 0 0-1.98-.36 1.8 1.8 0 0 0-1.08 1.65V21.5a2.1 2.1 0 1 1-4.2 0v-.09a1.8 1.8 0 0 0-1.08-1.65 1.8 1.8 0 0 0-1.98.36l-.06.06a2.1 2.1 0 1 1-2.97-2.97l.06-.06A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-1.65-1.08H2.8a2.1 2.1 0 1 1 0-4.2h.09A1.8 1.8 0 0 0 4.54 8.64a1.8 1.8 0 0 0-.36-1.98l-.06-.06a2.1 2.1 0 1 1 2.97-2.97l.06.06a1.8 1.8 0 0 0 1.98.36A1.8 1.8 0 0 0 10.2 2.4V2.3a2.1 2.1 0 1 1 4.2 0v.09a1.8 1.8 0 0 0 1.08 1.65 1.8 1.8 0 0 0 1.98-.36l.06-.06A2.1 2.1 0 1 1 20.5 6.6l-.06.06a1.8 1.8 0 0 0-.36 1.98 1.8 1.8 0 0 0 1.65 1.08h.09a2.1 2.1 0 1 1 0 4.2h-.09A1.8 1.8 0 0 0 19.4 15Z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                    </svg>
                </button>
            </div>
        </div>
    </div>

    <section class="course-config-panel" data-region="course-config-panel" hidden>
        <div class="course-config-header">
            <div>
                <h3 class="course-config-title">Course Configuration</h3>
                <p class="course-config-subtitle" data-region="course-config-course-label">Select a unit to configure notifications.</p>
            </div>
            <button type="button" class="course-config-close" data-region="course-config-close" aria-label="Close unit settings">&times;</button>
        </div>
        <form data-region="course-config-form">
            <input type="hidden" name="course_key" data-region="course-config-course-key">
            <input type="hidden" name="course_label" data-region="course-config-course-label-input">
            <input type="hidden" name="sesskey" value="{$moduleconfig['sesskey']}">

            <div class="course-config-grid">
                <div class="course-config-field">
                    <div class="course-config-label-row">
                        <label for="{$rootid}-teaching-mode">Teaching Mode / LMS Dependency</label>
                        <span class="course-config-help" tabindex="0" role="img" aria-label="How much the unit relies on Moodle activity data." data-tooltip="Controls how strongly missing Moodle activity should be interpreted. Use Low when important learning happens outside Moodle.">i</span>
                    </div>
                    <select id="{$rootid}-teaching-mode" name="teaching_mode" data-region="course-config-teaching-mode">
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                    </select>
                    <p class="course-config-note">Select Low if most teaching and interactions occur outside Moodle.</p>
                </div>

                <fieldset class="course-config-field">
                    <legend class="course-config-legend">
                        <span class="course-config-label-row">
                            Early Engagement Notifications
                            <span class="course-config-help" tabindex="0" role="img" aria-label="No LMS activity notification timing." data-tooltip="Choose when to notify you if students have no Moodle activity early in the teaching period.">i</span>
                        </span>
                    </legend>
                    <div class="course-config-checks">
                        <label class="course-config-check"><input type="checkbox" name="notify_week1_no_activity" value="1" data-region="course-config-week1"> Week 1 no LMS activity</label>
                        <label class="course-config-check"><input type="checkbox" name="notify_week2_no_activity" value="1" data-region="course-config-week2"> Week 2 still no activity</label>
                        <label class="course-config-check"><input type="checkbox" name="notify_week3_no_activity" value="1" data-region="course-config-week3"> Week 3 still no activity</label>
                    </div>
                </fieldset>

                <div class="course-config-field">
                    <div class="course-config-label-row">
                        <label for="{$rootid}-risk-threshold-config">Risk Threshold</label>
                        <span class="course-config-help" tabindex="0" role="img" aria-label="Prediction risk notification threshold." data-tooltip="Students are treated as notification candidates when their predicted final risk is greater than this value. Default is 0.50.">i</span>
                    </div>
                    <input id="{$rootid}-risk-threshold-config" type="number" name="risk_threshold" min="0" max="1" step="0.05" data-region="course-config-risk-threshold">
                    <p class="course-config-note">Notify me when predicted risk exceeds this value.</p>
                </div>

                <fieldset class="course-config-field is-wide">
                    <legend class="course-config-legend">
                        <span class="course-config-label-row">
                            Notification Types
                            <span class="course-config-help" tabindex="0" role="img" aria-label="Types of alerts to receive." data-tooltip="Select which course events should create alerts for this unit. These settings do not change prediction scores.">i</span>
                        </span>
                    </legend>
                    <div class="course-config-checks">
                        <label class="course-config-check"><input type="checkbox" name="notify_new_high_risk" value="1" data-region="course-config-new-high-risk"> New high-risk students</label>
                        <label class="course-config-check"><input type="checkbox" name="notify_no_lms_activity" value="1" data-region="course-config-no-lms"> No LMS activity</label>
                    </div>
                </fieldset>

                <div class="course-config-field">
                    <div class="course-config-label-row">
                        <label for="{$rootid}-notification-frequency">Notification Frequency</label>
                        <span class="course-config-help" tabindex="0" role="img" aria-label="How often alerts are delivered." data-tooltip="Controls whether alerts are sent as soon as they are detected, grouped weekly, or sent near the end of each teaching week.">i</span>
                    </div>
                    <select id="{$rootid}-notification-frequency" name="notification_frequency" data-region="course-config-frequency">
                        <option value="Immediately">Immediately</option>
                        <option value="Weekly summary">Weekly summary</option>
                        <option value="End of teaching week">End of teaching week</option>
                    </select>
                </div>
            </div>

            <div class="course-config-actions">
                <span class="course-config-status" data-region="course-config-status"></span>
                <button type="submit" class="course-config-save" data-region="course-config-save">Save Settings</button>
            </div>
        </form>
    </section>

    <section class="predictive-analytics-block">
        <div class="predictive-analytics-header">
            <h3 class="predictive-analytics-title">Predictive Analytics</h3>
            <p class="predictive-analytics-subtitle">Prediction distribution, student risk map, intervention list, and AI-supported interpretation.</p>
        </div>

    <h3 class="smartlmsdashboard-section-title">Student Risk Distribution</h3>
    <div class="risk-distribution-shell">
        <div class="risk-distribution-card">
            <div class="risk-distribution-chart-wrap">
                <canvas data-region="risk-chart"></canvas>
            </div>
        </div>
        <div class="risk-distribution-summary">
            <div>
                <h4 class="risk-summary-heading">Risk Overview</h4>
                <p class="risk-summary-subtext">Quick snapshot of the current student prediction distribution.</p>
            </div>
            <div class="risk-summary-stat-grid">
                <button type="button" class="risk-summary-stat is-blue" data-region="risk-summary-safe-card" data-risk-index="0">
                    <span class="risk-summary-stat-label">Not At-Risk</span>
                    <span class="risk-summary-stat-value" data-region="risk-summary-safe-count">0</span>
                </button>
                <button type="button" class="risk-summary-stat is-red" data-region="risk-summary-atrisk-card" data-risk-index="1">
                    <span class="risk-summary-stat-label">At-Risk</span>
                    <span class="risk-summary-stat-value" data-region="risk-summary-atrisk-count">0</span>
                </button>
                <button type="button" class="risk-summary-stat" data-region="risk-summary-safe-rate-card" data-risk-index="0">
                    <span class="risk-summary-stat-label">Not At-Risk Rate</span>
                    <span class="risk-summary-stat-value" data-region="risk-summary-safe-rate">0%</span>
                </button>
                <button type="button" class="risk-summary-stat" data-region="risk-summary-atrisk-rate-card" data-risk-index="1">
                    <span class="risk-summary-stat-label">At-Risk Rate</span>
                    <span class="risk-summary-stat-value" data-region="risk-summary-atrisk-rate">0%</span>
                </button>
            </div>
            <div class="risk-summary-highlight">
                <span class="risk-summary-highlight-label">Current Focus</span>
                <span class="risk-summary-highlight-value" data-region="risk-summary-focus">Total: 0</span>
            </div>
        </div>
    </div>

    <div class="risk-bubble-map-header">
        <h3 class="smartlmsdashboard-section-title">Student Risk Map</h3>
        <button type="button" class="risk-bubble-map-reset" data-region="risk-bubble-map-reset" aria-label="Reset Student Risk Map" title="Reset map">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M21 12a9 9 0 1 1-2.64-6.36" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                <path d="M21 3v6h-6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
            </svg>
        </button>
    </div>
    <p class="risk-bubble-context-note" data-region="risk-bubble-low-lms-note" hidden>Behaviour risk may be less reliable for this unit because Moodle engagement is configured as a weak signal.</p>
    <div class="risk-bubble-toolbar">
        <div class="risk-bubble-control">
            <label for="{$rootid}-bubble-filter">View</label>
            <select id="{$rootid}-bubble-filter" data-region="risk-bubble-filter">
                <option value="all">All Students</option>
                <option value="atrisk">Only At-Risk Students</option>
                <option value="top">Highest-Risk Students</option>
            </select>
        </div>

        <div class="risk-bubble-control" data-region="risk-bubble-topn-control">
            <label for="{$rootid}-bubble-topn">Number of Students</label>
            <input id="{$rootid}-bubble-topn" type="range" min="5" max="30" value="15" step="1" data-region="risk-bubble-topn">
            <span class="risk-bubble-value">Showing <span data-region="risk-bubble-topn-value">15</span> students</span>
        </div>

        <div class="risk-bubble-control">
            <label for="{$rootid}-bubble-threshold">Risk Threshold</label>
            <input id="{$rootid}-bubble-threshold" type="range" min="0" max="1" value="0.50" step="0.05" data-region="risk-bubble-threshold">
            <span class="risk-bubble-value">Threshold: <span data-region="risk-bubble-threshold-value">0.50</span></span>
        </div>

        <div class="risk-bubble-control">
            <label>Display Options</label>
            <div class="risk-bubble-toggle-row">
                <label class="risk-bubble-toggle" for="{$rootid}-bubble-jitter">
                    <input id="{$rootid}-bubble-jitter" type="checkbox" checked data-region="risk-bubble-jitter">
                    Improve readability
                </label>
                <span class="risk-bubble-tooltip" tabindex="0" role="img" aria-label="Slightly separates nearby student bubbles to make individual students easier to distinguish." data-tooltip="Slightly separates nearby student bubbles to make individual students easier to distinguish.">i</span>
                <label class="risk-bubble-toggle" for="{$rootid}-bubble-cluster">
                    <input id="{$rootid}-bubble-cluster" type="checkbox" checked data-region="risk-bubble-cluster">
                    Group overlapping students
                </label>
                <span class="risk-bubble-tooltip" tabindex="0" role="img" aria-label="Groups nearby students into clickable clusters. Click a cluster to select a student." data-tooltip="Groups nearby students into clickable clusters. Click a cluster to select a student.">i</span>
            </div>
        </div>
    </div>

    <div class="risk-bubble-chart-actions">
        <button type="button" class="risk-bubble-action-button" data-region="risk-bubble-reset-zoom" hidden>Reset zoom</button>
    </div>

    <div class="risk-bubble-chart-wrap">
        <canvas data-region="risk-bubble-chart"></canvas>
    </div>

    <div class="risk-bubble-selection-card">
        <div class="risk-bubble-selection-header">
            <div class="risk-bubble-selection-title-wrap">
                <h4 class="risk-bubble-selection-title">Student Details</h4>
                <p class="risk-bubble-selection-note" data-region="risk-bubble-selection-note">Click a bubble to inspect a student.</p>
            </div>
            <div class="risk-bubble-badge-stack">
                <span class="risk-bubble-badge" data-region="risk-bubble-selection-badge">No selection</span>
                <span class="risk-bubble-badge" data-region="risk-bubble-selection-zone-badge">No zone</span>
            </div>
        </div>

        <div class="risk-bubble-cluster-list" data-region="risk-bubble-cluster-list" hidden>
            <p class="risk-bubble-cluster-title" data-region="risk-bubble-cluster-title">Students in this cluster</p>
            <div class="risk-bubble-cluster-options" data-region="risk-bubble-cluster-options"></div>
        </div>

        <div class="risk-bubble-selection-grid">
            <div class="risk-bubble-selection-item">
                <span class="risk-bubble-selection-label">Student Name</span>
                <span class="risk-bubble-selection-value" data-region="risk-bubble-selection-student">Not selected</span>
            </div>
            <div class="risk-bubble-selection-item">
                <span class="risk-bubble-selection-label">Student ID</span>
                <span class="risk-bubble-selection-value" data-region="risk-bubble-selection-studentid">Not selected</span>
            </div>
            <div class="risk-bubble-selection-item">
                <span class="risk-bubble-selection-label">Email</span>
                <span class="risk-bubble-selection-value" data-region="risk-bubble-selection-email">Not selected</span>
            </div>
            <div class="risk-bubble-selection-item">
                <span class="risk-bubble-selection-label">Final Risk</span>
                <span class="risk-bubble-selection-value" data-region="risk-bubble-selection-risk">Not selected</span>
            </div>
            <div class="risk-bubble-selection-item">
                <span class="risk-bubble-selection-label">Behaviour Risk</span>
                <span class="risk-bubble-selection-value" data-region="risk-bubble-selection-behaviour">Not selected</span>
            </div>
            <div class="risk-bubble-selection-item">
                <span class="risk-bubble-selection-label">Academic Risk</span>
                <span class="risk-bubble-selection-value" data-region="risk-bubble-selection-academic">Not selected</span>
            </div>
        </div>

        <div class="uc-feedback-panel" data-region="uc-feedback-panel" hidden>
            <div class="uc-feedback-header">
                <div class="uc-feedback-heading">
                    <h4 class="uc-feedback-title">Provide Prediction Feedback</h4>
                    <p class="uc-feedback-note">Use this when your own assessment differs from, or adds context to, the model prediction.</p>
                </div>
            </div>
            <form data-region="uc-feedback-form">
                <input type="hidden" name="prediction_id" data-region="uc-feedback-prediction-id">
                <input type="hidden" name="student_key" data-region="uc-feedback-student-key">
                <input type="hidden" name="course_key" data-region="uc-feedback-course-key">
                <input type="hidden" name="snapshot_date" data-region="uc-feedback-snapshot-date">
                <input type="hidden" name="sesskey" value="{$moduleconfig['sesskey']}">

                <div class="uc-feedback-grid">
                    <div class="uc-feedback-field">
                        <label for="{$rootid}-uc-agreement">Do you agree with the prediction?</label>
                        <select id="{$rootid}-uc-agreement" name="uc_agreement" required>
                            <option value="">Select one</option>
                            <option value="Agree">Agree</option>
                            <option value="Disagree">Disagree</option>
                            <option value="Unsure">Unsure</option>
                        </select>
                    </div>
                    <div class="uc-feedback-field">
                        <label for="{$rootid}-uc-risk-level">UC risk assessment</label>
                        <select id="{$rootid}-uc-risk-level" name="uc_risk_level" required>
                            <option value="">Select one</option>
                            <option value="High">High</option>
                            <option value="Moderate">Moderate</option>
                            <option value="Low">Low</option>
                        </select>
                    </div>
                    <div class="uc-feedback-field">
                        <label for="{$rootid}-intervention-status">Intervention status</label>
                        <select id="{$rootid}-intervention-status" name="intervention_status" required>
                            <option value="">Select one</option>
                            <option value="Yes">Yes</option>
                            <option value="Planned">Planned</option>
                            <option value="No">No</option>
                        </select>
                    </div>
                </div>

                <fieldset class="uc-feedback-field uc-feedback-reason-field">
                    <legend class="uc-feedback-legend">Reason for assessment</legend>
                    <div class="uc-feedback-reasons">
                        <label class="uc-feedback-checkbox"><input type="checkbox" name="feedback_reason[]" value="Academic performance concern"> Academic performance concern</label>
                        <label class="uc-feedback-checkbox"><input type="checkbox" name="feedback_reason[]" value="Behaviour or engagement concern"> Behaviour or engagement concern</label>
                        <label class="uc-feedback-checkbox"><input type="checkbox" name="feedback_reason[]" value="Attendance or participation concern"> Attendance or participation concern</label>
                        <label class="uc-feedback-checkbox"><input type="checkbox" name="feedback_reason[]" value="Known personal or wellbeing context"> Known personal or wellbeing context</label>
                        <label class="uc-feedback-checkbox"><input type="checkbox" name="feedback_reason[]" value="Moodle data may be incomplete"> Moodle data may be incomplete</label>
                        <label class="uc-feedback-checkbox"><input type="checkbox" name="feedback_reason[]" value="Other"> Other</label>
                    </div>
                </fieldset>

                <div class="uc-feedback-field uc-feedback-comments-field">
                    <label for="{$rootid}-uc-comments">Optional comments</label>
                    <textarea id="{$rootid}-uc-comments" name="comments" placeholder="Additional comments (optional)"></textarea>
                </div>

                <div class="uc-feedback-actions">
                    <button type="button" class="risk-bubble-clear-selection" data-region="risk-bubble-clear-selection">Clear selection</button>
                    <div class="uc-feedback-submit-group">
                        <span class="uc-feedback-status" data-region="uc-feedback-status"></span>
                        <button type="submit" class="uc-feedback-submit" data-region="uc-feedback-submit">Save Feedback</button>
                    </div>
                </div>
            </form>
        </div>
    </div>

    <details class="risk-bubble-table-card">
        <summary>
            <span class="smartlmsdashboard-section-title">All At-Risk Students</span>
            <span class="risk-bubble-table-count" data-region="at-risk-count">0 students</span>
        </summary>
        <p class="risk-bubble-table-note">Detailed list of students flagged as at-risk in the latest prediction snapshot.</p>
        <div class="risk-bubble-table-toolbar">
            <div class="risk-bubble-table-control">
                <label for="{$rootid}-table-search">Search students</label>
                <input id="{$rootid}-table-search" type="search" placeholder="Search by ID, name, or email" data-region="at-risk-search">
            </div>
            <div class="risk-bubble-table-control">
                <label for="{$rootid}-table-sort">Sort by</label>
                <select id="{$rootid}-table-sort" data-region="at-risk-sort">
                    <option value="risk-desc">Final Risk: High to Low</option>
                    <option value="risk-asc">Final Risk: Low to High</option>
                    <option value="student-asc">Student Name: A to Z</option>
                    <option value="studentid-asc">Student ID: Low to High</option>
                    <option value="y-desc">Academic Risk: High to Low</option>
                    <option value="x-desc">Behaviour Risk: High to Low</option>
                </select>
            </div>
            <div class="risk-bubble-table-control">
                <label for="{$rootid}-table-pagesize">Rows per page</label>
                <select id="{$rootid}-table-pagesize" data-region="at-risk-pagesize">
                    <option value="10">10</option>
                    <option value="25" selected>25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                </select>
            </div>
            <div class="risk-bubble-table-actions">
                <button type="button" class="risk-bubble-table-button" data-region="at-risk-export">Export CSV</button>
            </div>
        </div>
        <div class="risk-bubble-table-wrap">
            <table class="risk-bubble-table">
                <thead>
                    <tr>
                        <th><button type="button" data-sort-key="studentid">Student ID</button></th>
                        <th><button type="button" data-sort-key="student">Name</button></th>
                        <th><button type="button" data-sort-key="email">Email</button></th>
                        <th><button type="button" data-sort-key="risk">Final Risk</button></th>
                        <th><button type="button" data-sort-key="x">Behaviour Risk</button></th>
                        <th><button type="button" data-sort-key="y">Academic Risk</button></th>
                    </tr>
                </thead>
                <tbody data-region="at-risk-table-body"></tbody>
            </table>
        </div>
        <div class="risk-bubble-pagination">
            <span class="risk-bubble-pagination-status" data-region="at-risk-pagination-status">Showing 0 of 0 students</span>
            <div class="risk-bubble-pagination-controls">
                <button type="button" data-region="at-risk-prev">Previous</button>
                <button type="button" data-region="at-risk-next">Next</button>
            </div>
        </div>
    </details>

    <section class="ai-insight-summary" data-region="ai-insight-summary">
        <div class="ai-insight-header">
            <div>
                <h4 class="ai-insight-title">AI Insight Summary</h4>
                <p class="ai-insight-subtitle">What Unit Coordinator should know from the latest prediction snapshot.</p>
            </div>
        </div>

        <div class="ai-insight-grid">
            <div class="ai-insight-card">
                <span class="ai-insight-card-label">Students Analysed</span>
                <span class="ai-insight-card-value" data-region="ai-insight-distribution">Loading...</span>
            </div>
            <div class="ai-insight-card">
                <span class="ai-insight-card-label">At-Risk Rate</span>
                <span class="ai-insight-card-value" data-region="ai-insight-map">Loading...</span>
            </div>
            <div class="ai-insight-card">
                <span class="ai-insight-card-label">Primary Concern</span>
                <span class="ai-insight-card-value" data-region="ai-insight-table">Loading...</span>
            </div>
        </div>

        <div class="ai-insight-copy">
            <div class="ai-insight-copy-block">
                <p class="ai-insight-copy-title">AI Summary</p>
                <p class="ai-insight-copy-text" data-region="ai-insight-user-summary">The dashboard is preparing a summary from the latest prediction snapshot.</p>
            </div>
            <div class="ai-insight-copy-block is-finding">
                <p class="ai-insight-copy-title">Key Findings</p>
                <ul class="ai-insight-list" data-region="ai-insight-chart-interpretation">
                    <li>Key findings will appear after the dashboard data loads.</li>
                </ul>
            </div>
            <div class="ai-insight-copy-block is-action">
                <p class="ai-insight-copy-title">Recommended Next Steps</p>
                <ul class="ai-insight-list" data-region="ai-insight-action-template">
                    <li>Recommended next steps will appear after the dashboard data loads.</li>
                </ul>
            </div>
        </div>
    </section>

    <footer class="prediction-info-footer">
        <p class="prediction-info-footer-title">Prediction Information</p>
        <div class="ai-insight-metadata-grid">
            <div class="ai-insight-meta-card">
                <span class="ai-insight-meta-label">Prediction Date:</span>
                <span class="ai-insight-meta-value" data-region="ai-insight-snapshot-date">Loading...</span>
            </div>
            <div class="ai-insight-meta-card">
                <span class="ai-insight-meta-label">Model Version:</span>
                <span class="ai-insight-meta-value" data-region="ai-insight-model-version">Loading...</span>
            </div>
            <div class="ai-insight-meta-card">
                <span class="ai-insight-meta-label">Model Confidence:</span>
                <span class="ai-insight-meta-value" data-region="ai-insight-confidence">Loading...</span>
            </div>
        </div>
    </footer>
    </section>
</div>
HTML;

        $this->content->footer = '';

        return $this->content;
    }
}
